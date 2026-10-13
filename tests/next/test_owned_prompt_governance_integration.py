"""Scope: render real TypeScript governance from an owned Git checkout."""

import re
from pathlib import Path

import pytest

from charter.activation.compiler import compile_charter, write_compiled_charter
from charter.activation.interview import apply_answer_overrides, default_interview
from runtime.next.prompt_builder import build_prompt
from tests.next.test_owned_implement_next_integration import _add_origin
from tests._factories import provision_test_charter
from tests.status.test_status_owned_checkout_seam import MISSION_SLUG, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


def test_owned_typescript_prompt_has_real_governance_without_python_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    primary, owned, mission_dir = _init_owned_mission(tmp_path)
    _add_origin(primary, tmp_path)
    monkeypatch.chdir(owned)
    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={
            "project_intent": "Build a TypeScript service.",
            "languages_frameworks": "TypeScript 5, Node.js, and repo-local tooling.",
            "testing_requirements": "Vitest for unit and integration checks.",
            "quality_gates": "Project tests pass and project lint/type-check commands pass.",
        },
        selected_paradigms=[], selected_directives=[], available_tools=["git", "pnpm"],
    )
    charter_dir = owned / ".kittify" / "charter"
    provision_test_charter(owned)
    charter_dir.mkdir(parents=True, exist_ok=True)
    compiled = compile_charter(mission="software-dev", interview=interview, repo_root=owned)
    (charter_dir / "charter.md").write_text(compiled.markdown, encoding="utf-8")
    write_compiled_charter(charter_dir, compiled, force=True, repo_root=owned)

    # Assumption check
    assert (owned / ".git").is_file()
    assert (charter_dir / "charter.md").is_file()

    # Act
    text, path = build_prompt(
        action="implement", feature_dir=mission_dir, mission_slug=MISSION_SLUG,
        wp_id="WP01", agent="codex", repo_root=owned, mission_type="software-dev", effective_root=owned,
    )

    # Assert
    assert "Governance: unavailable" not in text
    assert "TypeScript 5" in text
    assert "Vitest" in text
    sanitized = text.lower().replace(str(tmp_path).lower(), "").replace(tmp_path.as_posix().lower(), "")
    for forbidden in (r"\bpytest\b", r"\bjunit\b", r"\bmypy\b", r"\bruff\b", r"\bcargo\b", r"\bjest\b"):
        assert re.search(forbidden, sanitized) is None
    assert path.is_file()
