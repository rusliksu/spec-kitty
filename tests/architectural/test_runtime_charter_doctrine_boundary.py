"""Runtime reaches doctrine through the charter boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = _REPO_ROOT / "src" / "specify_cli"
_EXEMPT_ROOT = _RUNTIME_ROOT / "doctrine"


def _has_module_level_doctrine_import(source: str) -> bool:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "doctrine" or module.startswith("doctrine."):
                return True
        if isinstance(node, ast.Import) and any(alias.name == "doctrine" or alias.name.startswith("doctrine.") for alias in node.names):
            return True
    return False


def _is_exempt(path: Path) -> bool:
    try:
        path.relative_to(_EXEMPT_ROOT)
    except ValueError:
        return False
    return True


def test_boundary_predicate_has_prohibited_and_compliant_controls() -> None:
    assert _has_module_level_doctrine_import("from doctrine.resolver import resolve_profile\n")
    assert not _has_module_level_doctrine_import("from charter.profiles import resolve_profile\n")


def test_runtime_has_no_direct_doctrine_imports() -> None:
    violators: list[str] = []
    for path in sorted(_RUNTIME_ROOT.rglob("*.py")):
        if _is_exempt(path):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _has_module_level_doctrine_import(source):
            violators.append(str(path.relative_to(_REPO_ROOT)))

    assert not violators, "runtime must reach doctrine through charter; direct imports: " + ", ".join(violators)
