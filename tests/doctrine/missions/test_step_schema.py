"""Field-round-trip + absence-tolerance tests for the S-B schema foundation (WP01).

Covers:
- All net-new ``MissionStep`` fields (``sequence_index``, ``in_action_sequence``,
  ``recommended_model_tier``, ``template``) survive a load through
  :class:`~charter.offering.missions.mission_step_repository.MissionStepRepository` —
  guards against the ``extra="forbid"`` silent-strip trap when a new field is
  added to the model but not registered in ``_STEP_YAML_TO_MODEL``.
- ``MissionStep.prompt_template`` stays a required field (not relaxed).
- ``MissionType`` loads with ``action_sequence`` present (transitional,
  YAML-authored) and absent (post-cutover-tolerant). ``template_set`` is no
  longer a ``MissionType`` field (S-C cutover, mission-step-creatability-01KXQA6R
  WP01) -- authoring it now raises ``ValidationError`` (SC-002).

FR-001, FR-006, FR-007, FR-014 (S-B, mission-step-authority-01KXNZMT WP01).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from charter.offering.missions.mission_step_repository import MissionStepRepository
from charter.offering.missions.models import MissionStep, MissionStepTemplateRef, MissionType

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_step_yaml(root: Path, mission_type_id: str, step_id: str, body: str) -> Path:
    """Write *body* verbatim as ``step.yaml`` at the resolver's expected path."""
    step_dir = root / mission_type_id / step_id
    step_dir.mkdir(parents=True, exist_ok=True)
    step_file = step_dir / "step.yaml"
    step_file.write_text(body, encoding="utf-8")
    return step_file


# ---------------------------------------------------------------------------
# T004 — MissionStep field-round-trip (extra="forbid" strip guard)
# ---------------------------------------------------------------------------


def test_concurrent_loads_preserve_each_step_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overlapping parser lifetimes must not lose or exchange valid steps."""
    # Arrange
    for step_id, artifact_key in (("specify", "spec"), ("plan", "plan")):
        _write_step_yaml(
            tmp_path, "software-dev", step_id,
            f"id: {step_id}\ndisplay_name: {step_id}\nstep_type: agent\nprompt_template: prompt.md\n"
            f"template:\n  artifact_key: {artifact_key}\n"
            f"  template_file: {artifact_key}-template.md\n",
        )
    repo = MissionStepRepository(tmp_path)
    first_ready, second_ready, first_done = Event(), Event(), Event()
    scheduling_errors: list[str] = []
    prepare = YAML.get_constructor_parser

    def interleaved_prepare(loader: YAML, stream: Any) -> Any:
        constructor_parser = prepare(loader, stream)
        if stream.startswith("id: specify\n"):
            first_ready.set()
            if not second_ready.wait(10):
                scheduling_errors.append("second parser was not prepared")
        else:
            second_ready.set()
            if not first_done.wait(10):
                scheduling_errors.append("first parse did not finish")
        return constructor_parser

    def load_first() -> MissionStep | None:
        try:
            return repo.resolve("software-dev", "specify")
        finally:
            first_done.set()

    # Assumption check: the same documents load correctly without overlap.
    assert repo.resolve("software-dev", "specify") is not None
    assert repo.resolve("software-dev", "plan") is not None
    monkeypatch.setattr(YAML, "get_constructor_parser", interleaved_prepare)
    # Act: prepare the second parser before consuming the first document.
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(load_first)
        assert first_ready.wait(10), "first parser was not prepared"
        second = pool.submit(repo.resolve, "software-dev", "plan")
        spec_step = first.result(timeout=20)
        plan_step = second.result(timeout=20)
    # Assert
    assert not scheduling_errors, scheduling_errors
    assert spec_step is not None
    assert plan_step is not None
    assert (spec_step.id, spec_step.template) == (
        "specify", MissionStepTemplateRef(artifact_key="spec", template_file="spec-template.md"),
    )
    assert (plan_step.id, plan_step.template) == (
        "plan", MissionStepTemplateRef(artifact_key="plan", template_file="plan-template.md"),
    )


class TestMissionStepFieldRoundTrip:
    """Every new S-B field must survive load through the repository.

    ``MissionStep`` is ``extra="forbid"``; a field missing from
    ``_STEP_YAML_TO_MODEL`` is silently stripped rather than raising — this
    class is the regression guard for that trap (plan.md IC-01 risk).
    """

    def test_all_new_fields_survive_repository_load(self, tmp_path: Path) -> None:
        _write_step_yaml(
            tmp_path,
            "software-dev",
            "specify",
            """\
id: specify
display_name: Specification
step_type: agent
prompt_template: prompt.md
agent_profile: architect-alphonso
sequence_index: 0
in_action_sequence: true
recommended_model_tier: opus
template:
  artifact_key: spec
  template_file: spec-template.md
""",
        )
        repo = MissionStepRepository(tmp_path)

        step = repo.resolve("software-dev", "specify")

        assert step is not None
        assert step.id == "specify"
        assert step.agent_profile == "architect-alphonso"
        assert step.sequence_index == 0
        assert step.in_action_sequence is True
        assert step.recommended_model_tier == "opus"
        assert step.template == MissionStepTemplateRef(
            artifact_key="spec", template_file="spec-template.md"
        )

    def test_new_fields_default_when_absent_from_yaml(self, tmp_path: Path) -> None:
        """A step.yaml that predates S-B (no new keys) still loads with safe defaults."""
        _write_step_yaml(
            tmp_path,
            "software-dev",
            "retrospect",
            """\
id: retrospect
display_name: Retrospective
step_type: agent
prompt_template: prompt.md
""",
        )
        repo = MissionStepRepository(tmp_path)

        step = repo.resolve("software-dev", "retrospect")

        assert step is not None
        assert step.sequence_index is None
        assert step.in_action_sequence is False
        assert step.recommended_model_tier is None
        assert step.template is None

    def test_in_action_sequence_false_round_trips(self, tmp_path: Path) -> None:
        """A non-sequence step (e.g. retrospect) can explicitly assert membership=false."""
        _write_step_yaml(
            tmp_path,
            "software-dev",
            "retrospect",
            """\
id: retrospect
display_name: Retrospective
step_type: agent
prompt_template: prompt.md
sequence_index:
in_action_sequence: false
""",
        )
        repo = MissionStepRepository(tmp_path)

        step = repo.resolve("software-dev", "retrospect")

        assert step is not None
        assert step.sequence_index is None
        assert step.in_action_sequence is False


# ---------------------------------------------------------------------------
# prompt_template stays required (operator directive; NOT relaxed by S-B)
# ---------------------------------------------------------------------------


class TestPromptTemplateStaysRequired:
    """``prompt_template`` must remain a required ``str`` — S-B does not relax it."""

    def test_missing_prompt_template_rejected_by_model(self) -> None:
        with pytest.raises(ValidationError):
            MissionStep(
                id="specify",
                display_name="Specification",
                step_type="agent",
            )  # type: ignore[call-arg]

    def test_step_yaml_without_prompt_template_fails_to_resolve(self, tmp_path: Path) -> None:
        """The repository swallows validation failures as ``None`` (no raise)."""
        _write_step_yaml(
            tmp_path,
            "software-dev",
            "specify",
            """\
id: specify
display_name: Specification
step_type: agent
""",
        )
        repo = MissionStepRepository(tmp_path)

        assert repo.resolve("software-dev", "specify") is None

    def test_new_fields_do_not_make_prompt_template_optional(self) -> None:
        """Supplying every new S-B field still does not excuse prompt_template."""
        with pytest.raises(ValidationError, match="prompt_template"):
            MissionStep(
                id="specify",
                display_name="Specification",
                step_type="agent",
                sequence_index=0,
                in_action_sequence=True,
                recommended_model_tier="opus",
                template=MissionStepTemplateRef(
                    artifact_key="spec", template_file="spec-template.md"
                ),
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# MissionType — absence-tolerant action_sequence / template_set
# ---------------------------------------------------------------------------


class TestMissionTypeAbsenceTolerant:
    """``MissionType`` loads with the flat ``action_sequence`` projection field
    present or absent. ``template_set`` was retired as a ``MissionType``
    field entirely (S-C cutover, mission-step-creatability-01KXQA6R WP01,
    FR-001) -- ``TestTemplateSetRetiredFailsLoudly`` below covers its
    replacement contract."""

    def test_loads_with_action_sequence_present(self) -> None:
        mt = MissionType(
            id="software-dev",
            display_name="Software Development",
            action_sequence=["specify", "plan", "tasks", "implement", "review"],
        )

        assert mt.action_sequence == ["specify", "plan", "tasks", "implement", "review"]

    def test_loads_with_action_sequence_absent(self) -> None:
        """Post-WP07-cutover shape: the flat field is not authored in the YAML."""
        mt = MissionType(
            id="documentation",
            display_name="Documentation",
        )

        assert mt.action_sequence is None

    def test_absent_action_sequence_does_not_trip_non_empty_invariant(self) -> None:
        """Absence is not the same as an authored-empty list — must not raise."""
        mt = MissionType(id="research", display_name="Research")

        assert mt.action_sequence is None


class TestTemplateSetRetiredFailsLoudly:
    """SC-002 (S-C cutover, mission-step-creatability-01KXQA6R WP01, FR-001):
    the retired ``template_set`` field is rejected loudly, not silently
    honored or dropped, by ``extra="forbid"``."""

    def test_authoring_template_set_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="template_set"):
            MissionType(
                id="software-dev",
                display_name="Software Development",
                action_sequence=["specify"],
                template_set={"spec": "spec-template.md"},  # type: ignore[call-arg]
            )
