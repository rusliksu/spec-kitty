"""Declared linked checkouts must pass their own project schema gate."""

from pathlib import Path
import sys

import pytest
import typer
from click import Command

import specify_cli
from tests.status.test_status_owned_checkout_seam import _file_bytes, _init_owned_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.mark.parametrize("schema", [2, 100])
@pytest.mark.parametrize("flag_form", ["separate", "equals"])
def test_owned_startup_refuses_incompatible_target_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, schema: int, flag_form: str,
) -> None:
    primary, owned, _ = _init_owned_mission(tmp_path)
    for root, version in [(primary, 3), (owned, schema)]:
        (root / ".kittify" / "metadata.yaml").write_text(
            f"spec_kitty:\n  schema_version: {version}\n", encoding="utf-8",
        )
    monkeypatch.chdir(primary)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    flag = ["--owned-checkout", str(owned)] if flag_form == "separate" else [f"--owned-checkout={owned}"]
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "agent", "action", "implement", "WP01", *flag])
    before = _file_bytes(primary), _file_bytes(owned)
    ctx = typer.Context(Command("spec-kitty"))
    ctx.invoked_subcommand = "agent"

    with pytest.raises(SystemExit) as refusal:
        specify_cli._run_startup_project_gates(ctx)

    assert refusal.value.code != 0
    assert (_file_bytes(primary), _file_bytes(owned)) == before
