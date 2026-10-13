"""An owned invocation still checks the project without rewriting global assets."""

from pathlib import Path
import sys

from click import Command
import pytest
import typer

import specify_cli
from specify_cli.runtime import agent_commands, bootstrap

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize("args, expected", [
    (["agent", "action", "implement"], None),
    (["--owned-checkout", "a b"], Path("a b")),
    (["--owned-checkout=a b"], Path("a b")),
    (["--owned-checkout=first", "--owned-checkout", "last"], Path("last")),
])
def test_owned_argument_parser_preserves_native_last_option_semantics(args: list[str], expected: Path | None) -> None:
    assert specify_cli._owned_checkout_argument(["spec-kitty", *args]) == expected


@pytest.mark.parametrize("args", [["--owned-checkout"], ["--owned-checkout="], ["--owned-checkout", "--json"]])
def test_owned_argument_parser_refuses_missing_path(args: list[str]) -> None:
    with pytest.raises(typer.BadParameter, match="requires a path"):
        specify_cli._owned_checkout_argument(["spec-kitty", *args])


def test_owned_invocation_keeps_project_gate_and_preserves_global_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    global_asset = tmp_path / "global-command.md"
    global_asset.write_text("Existing installed command.\n", encoding="utf-8")
    monkeypatch.setattr(specify_cli, "root_callback", lambda ctx: None)
    monkeypatch.setattr(bootstrap, "ensure_runtime", lambda: global_asset.write_text("Runtime replaced.\n", encoding="utf-8"))
    monkeypatch.setattr(agent_commands, "ensure_global_agent_commands", lambda: global_asset.write_text("Command replaced.\n", encoding="utf-8"))
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "agent", "action", "implement", "WP01", "--owned-checkout", str(tmp_path)])

    def refuse_project(ctx: typer.Context) -> None:
        raise RuntimeError("Unmigrated project refused")

    monkeypatch.setattr(specify_cli, "_run_startup_project_gates", refuse_project)
    ctx = typer.Context(Command("spec-kitty"))

    # Assumption check
    assert global_asset.read_text(encoding="utf-8") == "Existing installed command.\n"

    # Act / Assert
    with pytest.raises(RuntimeError, match="Unmigrated project refused"):
        specify_cli.main_callback(ctx)
    assert global_asset.read_text(encoding="utf-8") == "Existing installed command.\n"
