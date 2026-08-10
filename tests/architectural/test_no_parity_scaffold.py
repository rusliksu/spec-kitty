"""Current configured-template authority guards.

The transitional parity artifact/name sweep is retired. These checks exercise
the live configured-template readers and exact typeless compatibility boundary.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_READER = _REPO_ROOT / "src/specify_cli/core/mission_creation.py"
_PLAN_READER = _REPO_ROOT / "src/specify_cli/cli/commands/agent/mission_setup_plan.py"


def _function(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(matches) == 1, f"Expected exactly one {name}() in {path}"
    return matches[0]


def _qualified_name(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        owner = _qualified_name(node.value)
        return (*owner, node.attr) if owner else ()
    return ()


def _calls(function: ast.FunctionDef, qualified_name: tuple[str, ...]) -> list[ast.Call]:
    return [node for node in ast.walk(function) if isinstance(node, ast.Call) and _qualified_name(node.func) == qualified_name]


def _first_string_argument(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first = call.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def _is_exact_typeless_legacy_guard(node: ast.If, legacy_call: ast.Call) -> bool:
    match node.test:
        case ast.Compare(
            left=ast.Attribute(
                value=ast.Name(id="resolved_mission_type"),
                attr="mission_type",
            ),
            ops=[ast.Is()],
            comparators=[ast.Constant(value=None)],
        ):
            return not node.orelse and any(isinstance(statement, ast.Return) and statement.value is legacy_call for statement in node.body)
        case _:
            return False


def test_production_readers_use_configured_mapping_seam() -> None:
    """Reader call sites select semantic keys, not magic template filenames."""
    spec_reader = _function(_SPEC_READER, "create_mission_core")
    plan_reader = _function(_PLAN_READER, "_resolve_plan_template")

    spec_calls = _calls(spec_reader, ("resolve_configured_template",))
    plan_calls = _calls(plan_reader, ("_mission", "resolve_configured_template"))
    assert [_first_string_argument(call) for call in spec_calls] == ["spec"]
    assert [_first_string_argument(call) for call in plan_calls] == ["plan"]

    assert not _calls(spec_reader, ("resolve_template",))
    spec_literals = {node.value for node in ast.walk(spec_reader) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "spec-template.md" not in spec_literals
    assert "software-dev-default" not in spec_literals


def test_plan_legacy_selector_is_confined_to_typeless_compatibility_branch() -> None:
    """The temporary #2660 boundary cannot become the activated reader path."""
    plan_reader = _function(_PLAN_READER, "_resolve_plan_template")
    legacy_calls = _calls(plan_reader, ("_mission", "resolve_template"))
    assert len(legacy_calls) == 1
    legacy_call = legacy_calls[0]
    assert _first_string_argument(legacy_call) == "plan-template.md"

    typeless_guard = next(
        (node for node in ast.walk(plan_reader) if isinstance(node, ast.If) and _is_exact_typeless_legacy_guard(node, legacy_call)),
        None,
    )
    assert typeless_guard is not None, "Legacy plan selection escaped its exact `mission_type is None` body"
    configured_calls = _calls(plan_reader, ("_mission", "resolve_configured_template"))
    assert [_first_string_argument(call) for call in configured_calls] == ["plan"]

    plan_literals = {node.value for node in ast.walk(plan_reader) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "software-dev-default" not in plan_literals


@pytest.mark.parametrize(
    ("operator", "expected"),
    [("is", True), ("is not", False)],
)
def test_typeless_guard_helper_rejects_inverse_mutation(
    operator: str,
    expected: bool,
) -> None:
    function = ast.parse(
        "def reader(resolved_mission_type):\n"
        f"    if resolved_mission_type.mission_type {operator} None:\n"
        "        return resolve_template('plan-template.md')\n"
        "    return resolve_configured_template('plan')\n"
    ).body[0]
    assert isinstance(function, ast.FunctionDef)
    guard = function.body[0]
    assert isinstance(guard, ast.If)
    legacy_call = _calls(function, ("resolve_template",))[0]

    assert _is_exact_typeless_legacy_guard(guard, legacy_call) is expected


@pytest.mark.parametrize(
    "receiver",
    ["context", "other", "resolved_mission_type.context"],
)
def test_typeless_guard_helper_rejects_wrong_receiver(receiver: str) -> None:
    function = ast.parse(
        "def reader(resolved_mission_type):\n"
        f"    if {receiver}.mission_type is None:\n"
        "        return resolve_template('plan-template.md')\n"
        "    return resolve_configured_template('plan')\n"
    ).body[0]
    assert isinstance(function, ast.FunctionDef)
    guard = function.body[0]
    assert isinstance(guard, ast.If)
    legacy_call = _calls(function, ("resolve_template",))[0]

    assert not _is_exact_typeless_legacy_guard(guard, legacy_call)
