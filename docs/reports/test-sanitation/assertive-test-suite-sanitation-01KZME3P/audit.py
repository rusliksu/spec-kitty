#!/usr/bin/env python3
"""Mission-local, deterministic test-sanitation evidence auditor.

This file is deliberately not installed.  It combines independent AST source
discovery with pytest's collection hooks; neither view is allowed to silently
stand in for the other.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable, Iterable, Mapping, Sequence
import contextlib
import copy
import dataclasses
import datetime as dt
import fnmatch
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any, TypeVar, cast

import pytest
import yaml

SCHEMA = "test-sanitation/v1"
TARGET_INVENTORY_SHA = "28ae75ea998c898aba57364db7a06d2088bd2af2"
VERDICTS = {"KEEP", "CONSOLIDATE", "FIX_TEST", "FIX_PRODUCT", "DELETE", "TEMPORARY"}
PROFILES = {
    "inert", "duplicate", "structural", "contract", "slow", "flake",
    "dead_symbol", "route", "environmental_platform",
}
COLLECTION_STATES = {"collected", "ignored", "deselected", "error", "zero_node"}
OUTCOMES = {"passed", "failed", "error", "skipped", "xfailed", "xpassed", "not_run", None}
MEASUREMENT_OUTCOMES = {"passed", "failed", "error", "skipped", "xfailed", "xpassed", "not_run"}
GRANULARITIES = {"function", "family", "duplicate_cluster", "node"}
ROUTE_ROLES = {"owner", "coverage", "platform", "hard_gate"}
EQUIVALENCE_DIMENSIONS = {
    "production_path", "oracle", "outcome", "route_role", "cost_class", "platform", "disposition",
}
TEST_NAME = re.compile(r"^test(?:_|$)")
VOLATILE_TEMP = re.compile(
    r"(?:/private)?/var/folders/[^/]+/[^/]+/T/[^/\s'\"\]\),]+"
    r"|/tmp/[^/\s'\"\]\),]+"
)
F = TypeVar("F", bound=Callable[..., Any])


def hookimpl(**kwargs: Any) -> Callable[[F], F]:
    """Typed facade for pluggy's dynamically typed pytest decorator."""
    return cast(Callable[[F], F], pytest.hookimpl(**kwargs))


class AuditError(RuntimeError):
    """Fail-closed evidence validation error."""


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        # List order may encode argv, precedence, parameter, or event semantics.
        # Set-like lists are sorted explicitly where they are constructed.
        return [_stable(item) for item in value]
    if isinstance(value, str):
        return VOLATILE_TEMP.sub("<TEMP_ROOT>", value)
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode()
    # Mission evidence uses standard SHA-256 for portable file/body checksums.
    return hashlib.sha256(value).hexdigest()  # noqa: TID251


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    return ast.dump(node, annotate_fields=False, include_attributes=False)


def _shape(node: ast.AST) -> ast.AST:
    """Return a syntax-shape tree; never label this semantic equivalence."""
    tree = ast.parse(ast.unparse(node))
    for child in ast.walk(tree):
        if isinstance(child, ast.Constant):
            child.value = f"<{type(child.value).__name__}>"
        elif isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Store):
            child.id = "<name>"
        elif isinstance(child, ast.arg):
            child.arg = "<arg>"
    return tree


@dataclasses.dataclass(frozen=True)
class SourceUnit:
    id: str
    path: str
    qualname: str
    line: int
    decorators: tuple[str, ...]
    exact_body_sha256: str
    structural_shape_sha256: str
    inert_reasons: tuple[str, ...]


def _unit(
    path: str,
    qualname: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    inherited_decorators: Sequence[str] = (),
) -> SourceUnit:
    decorators = tuple(sorted({_decorator_name(item) for item in node.decorator_list} | set(inherited_decorators)))
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    # Strict duplicate identity intentionally ignores only docstrings.
    exact = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
    shape = ast.dump(_shape(ast.Module(body=node.body, type_ignores=[])), include_attributes=False)
    reasons: list[str] = []
    lowered = " ".join(decorators).lower()
    for marker in ("skip", "xfail", "quarantine", "flaky"):
        if re.search(rf"(?:^|\.){marker}(?:$|\s)", lowered):
            reasons.append(f"decorator:{marker}")
    if not body or all(isinstance(item, (ast.Pass, ast.Expr)) and (
        isinstance(item, ast.Pass)
        or (isinstance(item.value, ast.Constant) and item.value.value in (None, Ellipsis))
    ) for item in body):
        reasons.append("empty_body")
    for statement in body:
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and _decorator_name(statement.value.func) in {"skip", "pytest.skip"}
        ):
            reasons.append("body:unconditional_pytest.skip")
    return SourceUnit(
        id=f"{path}::{qualname}", path=path, qualname=qualname, line=node.lineno,
        decorators=decorators, exact_body_sha256=_sha(exact),
        structural_shape_sha256=_sha(shape), inert_reasons=tuple(sorted(set(reasons))),
    )


def discover_source(root: Path, tests_root: Path) -> tuple[list[SourceUnit], list[dict[str, str]]]:  # noqa: C901 - recursive AST forms
    units: list[SourceUnit] = []
    parse_errors: list[dict[str, str]] = []
    if not tests_root.exists():
        return units, parse_errors
    for file in sorted(tests_root.rglob("*.py")):
        rel = _rel(file, root)
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=rel)
        except (OSError, SyntaxError, UnicodeError) as exc:
            parse_errors.append({"path": rel, "error": _stable(str(exc))})
            continue
        module_markers: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                if any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets):
                    value = statement.value
                    if value is not None:
                        for child in ast.walk(value):
                            if isinstance(child, ast.Call):
                                module_markers.add(_decorator_name(child.func))
        def visit(body: Sequence[ast.stmt], prefix: tuple[str, ...], inherited: set[str], source_path: str = rel) -> None:
            for node in body:
                if isinstance(node, ast.ClassDef):
                    class_markers = inherited | {_decorator_name(item) for item in node.decorator_list}
                    visit(node.body, (*prefix, node.name), class_markers)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualname = ".".join((*prefix, node.name))
                    if TEST_NAME.match(node.name):
                        units.append(_unit(source_path, qualname, node, sorted(inherited)))
                    visit(node.body, (*prefix, node.name), inherited)
                else:
                    nested_bodies = [value for value in ast.iter_child_nodes(node) if isinstance(value, ast.stmt)]
                    if nested_bodies:
                        visit(nested_bodies, prefix, inherited)

        visit(tree.body, (), module_markers)
    return sorted(units, key=lambda item: item.id), parse_errors


def discover_config(root: Path) -> dict[str, Any]:
    files = ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"]
    result: dict[str, Any] = {"files": [], "collect_ignore": [], "collect_ignore_glob": []}
    for name in files:
        path = root / name
        if path.is_file():
            raw = path.read_bytes()
            result["files"].append({"path": name, "sha256": _sha(raw)})
    tests = root / "tests"
    for conftest in sorted(tests.rglob("conftest.py")) if tests.exists() else []:
        rel_parent = conftest.parent.relative_to(root)
        try:
            tree = ast.parse(conftest.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = statement.value
            for target in targets:
                if not isinstance(target, ast.Name) or target.id not in {"collect_ignore", "collect_ignore_glob"}:
                    continue
                try:
                    values = ast.literal_eval(value) if value is not None else []
                except (ValueError, TypeError):
                    values = ["<dynamic>"]
                for item in values if isinstance(values, (list, tuple)) else [values]:
                    text = str(item)
                    if text != "<dynamic>":
                        text = (rel_parent / text).as_posix()
                    result[target.id].append(text)
    return cast(dict[str, Any], _stable(result))


class CollectionPlugin:
    def __init__(self, root: Path, tests_root: Path) -> None:
        self.root = root
        self.tests_root = tests_root
        self.nodes: list[dict[str, Any]] = []
        self.deselected: list[str] = []
        self.deselected_items: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []
        self.internal_errors: list[str] = []
        self.ignored: set[str] = set()

    @hookimpl(wrapper=True, tryfirst=True)
    def pytest_ignore_collect(self, collection_path: Path, config: pytest.Config) -> Any:
        del config
        result = yield
        if result is True:
            path = Path(str(collection_path))
            if self.tests_root == path or self.tests_root in path.parents:
                self.ignored.add(_rel(path, self.root))
        return result

    @hookimpl(wrapper=True, trylast=True)
    def pytest_collection_modifyitems(self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> Any:
        del session, config
        try:
            result = yield
        except BaseException as exc:
            self.internal_errors.append(str(_stable(repr(exc))))
            raise
        for item in items:
            path, line, source_name = item.location
            effective_markers = list(item.iter_markers())
            marker_names = {marker.name for marker in effective_markers}
            reason = None
            for marker in effective_markers:
                if marker.name in {"skip", "skipif", "xfail", "quarantine"}:
                    raw_reason = marker.kwargs.get("reason") or (marker.args[0] if marker.args else marker.name)
                    reason = _stable(repr(raw_reason))
                    break
            self.nodes.append({
                "nodeid": item.nodeid.replace("\\", "/"),
                "path": Path(path).as_posix(), "line": int(line or 0) + 1,
                "parent_source_function": source_name.split("[")[0],
                # Arguments (especially parametrize payloads) are not inventory
                # identity and can be enormous; effective marker names plus the
                # dedicated skip/xfail reason retain every required distinction.
                "markers": sorted(marker_names),
                "quarantined": "quarantine" in marker_names,
                "skip_or_xfail_reason": reason,
            })
        return result

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        for item in items:
            path, line, source_name = item.location
            nodeid = item.nodeid.replace("\\", "/")
            self.deselected.append(nodeid)
            self.deselected_items.append({
                "nodeid": nodeid, "path": Path(path).as_posix(),
                "line": int(line or 0) + 1,
                "parent_source_function": source_name.split("[")[0],
            })

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.errors.append({"nodeid": report.nodeid.replace("\\", "/"), "error": _stable(str(report.longrepr))})

    def pytest_internalerror(self, excrepr: object, excinfo: object) -> None:
        del excinfo
        self.internal_errors.append(str(_stable(str(excrepr))))


def collect_pytest(root: Path, tests_root: Path, extra_args: Sequence[str]) -> dict[str, Any]:
    plugin = CollectionPlugin(root, tests_root)
    argv = [str(tests_root), "--collect-only", "-q", "-p", "no:cacheprovider", *extra_args]
    old = Path.cwd()
    try:
        os.chdir(root)
        # Hook data is authoritative; pytest's human node listing is intentionally
        # excluded from compact evidence.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = int(pytest.main(argv, plugins=[plugin]))
    finally:
        os.chdir(old)
    return cast(dict[str, Any], _stable({
        "argv": ["pytest", *argv], "exit_code": code,
        "nodes": sorted(plugin.nodes, key=lambda row: row["nodeid"]),
        "deselected": sorted(set(plugin.deselected)),
        "deselected_items": sorted(plugin.deselected_items, key=lambda row: row["nodeid"]),
        "collection_errors": sorted(plugin.errors, key=lambda row: row["nodeid"]),
        "internal_errors": sorted(set(plugin.internal_errors)),
        "ignored_paths": sorted(plugin.ignored),
    }))


def _source_matches(unit: SourceUnit, node: Mapping[str, Any]) -> bool:
    if unit.path != node["path"]:
        return False
    node_parts = str(node["nodeid"]).split("::")[1:]
    if node_parts:
        node_parts[-1] = node_parts[-1].split("[")[0]
    unit_parts = unit.qualname.split(".")
    return node_parts[-len(unit_parts):] == unit_parts


def load_owners(root: Path) -> dict[str, str]:
    tasks = root / "kitty-specs" / "assertive-test-suite-sanitation-01KZME3P" / "tasks"
    owners: dict[str, str] = {}
    collisions: list[str] = []
    for task in sorted(tasks.glob("WP*.md")):
        wp = task.name.split("-")[0]
        text = task.read_text(encoding="utf-8")
        match = re.search(r"(?m)^owned_files:\n(?P<body>(?:^- [^\n]+\n)+)", text)
        if not match:
            continue
        for line in match.group("body").splitlines():
            path = line[2:].strip().strip("`'")
            previous = owners.get(path)
            if previous and previous != wp:
                collisions.append(f"{path}: {previous}, {wp}")
            owners[path] = wp
    if collisions:
        raise AuditError("owned-file collisions: " + "; ".join(collisions))
    return owners


def _group_manifest(units: Sequence[SourceUnit], field: str, owners: Mapping[str, str]) -> list[dict[str, Any]]:
    groups: dict[str, list[SourceUnit]] = {}
    for unit in units:
        groups.setdefault(str(getattr(unit, field)), []).append(unit)
    result = []
    for fingerprint, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        rows = []
        for unit in members:
            rows.append({"member": unit.id, "path": unit.path, "owner": owners.get(unit.path)})
        result.append({"fingerprint": fingerprint, "members": rows})
    return result


def _scanner_files(root: Path, owners: Mapping[str, str]) -> list[dict[str, Any]]:
    rows = []
    architectural = root / "tests" / "architectural"
    explicit_non_arch = {
        "tests/sync/test_no_queue_drain_constructed_3030.py",
        "tests/specify_cli/coordination/test_simple_case_flat_topology.py",
        "tests/specify_cli/write_side/test_characterization_write_target.py",
    }
    candidates = set(architectural.rglob("test*.py")) if architectural.exists() else set()
    candidates.update(root / path for path in explicit_non_arch if (root / path).exists())
    repo_ast_paths: set[Path] = set()
    # AST scanners are AST parse calls over file-loaded source, not every test
    # that parses an inline snippet. Discover that precise shape under every root.
    tests_root = root / "tests"
    for path in sorted(tests_root.rglob("test*.py")) if tests_root.exists() else []:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        file_loaded_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                if isinstance(value, ast.Call) and _decorator_name(value.func).endswith((".read_text", ".read_bytes")):
                    file_loaded_names.update(target.id for target in targets if isinstance(target, ast.Name))
        repo_ast = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _decorator_name(node.func) != "ast.parse" or not node.args:
                continue
            argument = node.args[0]
            direct_read = isinstance(argument, ast.Call) and _decorator_name(argument.func).endswith((".read_text", ".read_bytes"))
            if direct_read or (isinstance(argument, ast.Name) and argument.id in file_loaded_names):
                repo_ast = True
                break
        if repo_ast:
            candidates.add(path)
            repo_ast_paths.add(path)
    for path in sorted(candidates):
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        kinds = ["structural"] if rel.startswith("tests/architectural/") or rel in explicit_non_arch else []
        if path in repo_ast_paths or ("structural" in kinds and ("ast.parse" in lowered or "ast.walk" in lowered)):
            kinds.append("ast")
        if any(token in lowered for token in ("src/specify_cli", "read_text(", "read_bytes(", "rglob(", "glob(")):
            kinds.append("source")
        if any(token in lowered for token in (" in source", "not in source", "count(", "re.search", "re.findall")):
            kinds.append("text")
        rows.append({"member": rel, "path": rel, "scanner_kinds": sorted(set(kinds)), "owner": owners.get(rel)})
    return rows


def _compact_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    nodes = cast(list[dict[str, Any]], collection["nodes"])
    paths = sorted({str(node["path"]) for node in nodes})
    functions = sorted({str(node["parent_source_function"]) for node in nodes})
    marker_sets = sorted({tuple(node["markers"]) for node in nodes})
    reasons = sorted({str(node["skip_or_xfail_reason"]) for node in nodes if node["skip_or_xfail_reason"] is not None})
    path_ref = {value: index for index, value in enumerate(paths)}
    function_ref = {value: index for index, value in enumerate(functions)}
    marker_ref = {value: index for index, value in enumerate(marker_sets)}
    reason_ref = {value: index for index, value in enumerate(reasons)}
    compact_nodes = []
    for node in nodes:
        reason = node["skip_or_xfail_reason"]
        compact_nodes.append([
            node["nodeid"], path_ref[node["path"]], node["line"], function_ref[node["parent_source_function"]],
            marker_ref[tuple(node["markers"])], node["quarantined"], None if reason is None else reason_ref[str(reason)],
        ])
    return {
        "argv": collection["argv"], "exit_code": collection["exit_code"],
        "node_fields": ["nodeid", "path_ref", "line", "parent_source_function_ref", "marker_set_ref", "quarantined", "reason_ref"],
        "tables": {"paths": paths, "parent_source_functions": functions, "marker_sets": [list(row) for row in marker_sets], "reasons": reasons},
        "nodes": compact_nodes,
        "deselected": collection["deselected"], "deselected_items": collection["deselected_items"],
        "collection_errors": collection["collection_errors"], "internal_errors": collection["internal_errors"],
        "ignored_paths": collection["ignored_paths"],
    }


def _reconcile(units: Sequence[SourceUnit], collection: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes = collection["nodes"]
    errors = collection["collection_errors"]
    deselected_items = cast(list[dict[str, Any]], collection.get("deselected_items", []))
    deselected_keys = {(str(row["path"]), str(row["parent_source_function"])) for row in deselected_items}
    ignored_cfg = [str(item) for item in config.get("collect_ignore", [])]
    ignored_glob = [str(item) for item in config.get("collect_ignore_glob", [])]
    ignored_observed = [str(item) for item in collection.get("ignored_paths", [])]
    rows: list[dict[str, Any]] = []
    member_counts = {str(node["nodeid"]): 0 for node in nodes}
    nodes_by_source: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for node in nodes:
        key = (str(node["path"]), str(node["parent_source_function"]))
        nodes_by_source.setdefault(key, []).append(node)
    for unit in units:
        matched = nodes_by_source.get((unit.path, unit.qualname), [])
        for node in matched:
            member_counts[str(node["nodeid"])] += 1
        path_error = any(unit.path == row["nodeid"] or unit.path.startswith(f"{row['nodeid']}/") for row in errors)
        ignored = (
            unit.path in ignored_cfg
            or any(unit.path == path or unit.path.startswith(f"{path}/") for path in ignored_observed)
            or any(fnmatch.fnmatch(unit.path, pat) for pat in ignored_glob)
        )
        matched_deselected = (unit.path, unit.qualname) in deselected_keys
        if matched:
            state = "collected"
        elif matched_deselected:
            state = "deselected"
        elif path_error:
            state = "error"
        elif ignored:
            state = "ignored"
        else:
            state = "zero_node"
        rows.append({**dataclasses.asdict(unit), "collection_state": state, "nodeids": sorted(node["nodeid"] for node in matched), "zero_node": not matched})
    bad_nodes = sorted(nodeid for nodeid, count in member_counts.items() if count != 1)
    counts = {state: sum(row["collection_state"] == state for row in rows) for state in sorted(COLLECTION_STATES)}
    return rows, {
        "source_units": len(units), "collected_nodes": len(nodes), "state_counts": counts,
        "unreconciled_or_duplicate_nodes": bad_nodes,
        "complete": (
            not bad_nodes and len(rows) == len(units)
            and int(collection["exit_code"]) in {0, 5}
            and not collection.get("internal_errors")
            and not collection.get("collection_errors")
        ),
    }


def snapshot(root: Path, tests_path: str, extra_args: Sequence[str], inventory_sha: str | None) -> dict[str, Any]:
    root = root.resolve()
    tests_root = (root / tests_path).resolve()
    units, parse_errors = discover_source(root, tests_root)
    test_files = sorted(_rel(path, root) for path in tests_root.rglob("*.py")) if tests_root.exists() else []
    unit_paths = {unit.path for unit in units}
    config = discover_config(root)
    collection = collect_pytest(root, tests_root, extra_args) if tests_root.exists() else {
        "argv": ["pytest", tests_path, "--collect-only", "-q", "-p", "no:cacheprovider"],
        "exit_code": 5, "nodes": [], "deselected": [], "deselected_items": [],
        "collection_errors": [], "internal_errors": [], "ignored_paths": [],
    }
    rows, reconciliation = _reconcile(units, collection, config)
    owners = load_owners(root) if (root / "kitty-specs" / "assertive-test-suite-sanitation-01KZME3P" / "tasks").exists() else {}
    exact = _group_manifest(units, "exact_body_sha256", owners)
    collection_nodes = cast(list[dict[str, Any]], collection["nodes"])
    nodes_by_id = {node["nodeid"]: node for node in collection_nodes}
    inert = []
    for row in rows:
        reasons = set(row["inert_reasons"])
        if not reasons:
            continue
        for nodeid in row["nodeids"]:
            for marker in nodes_by_id[nodeid]["markers"]:
                if marker in {"skip", "skipif", "xfail", "quarantine", "flaky"}:
                    reasons.add(f"effective_marker:{marker}")
        inert.append({"member": row["id"], "path": row["path"], "reasons": sorted(reasons), "owner": owners.get(row["path"])})
    scanners = _scanner_files(root, owners)
    manifests = {
        "inert_candidates": inert,
        "exact_body_groups": exact,
        "promoted_semantic_groups": [],
        "structural_shape_index": {
            "group_count": len({unit.structural_shape_sha256 for unit in units}),
            "sha256": _sha("\n".join(sorted(unit.structural_shape_sha256 for unit in units))),
        },
        "scanner_candidates": scanners,
    }
    unowned = []
    for row in inert + scanners:
        if not row["owner"]:
            unowned.append(row["member"])
    for group in exact:
        unowned.extend(row["member"] for row in group["members"] if not row["owner"])
    node_ref = {node["nodeid"]: index for index, node in enumerate(collection_nodes)}
    compact_rows = []
    for row in rows:
        compact = dict(row)
        compact["node_refs"] = [node_ref[nodeid] for nodeid in compact.pop("nodeids")]
        compact_rows.append(compact)
    evidence = {
        "schema_version": SCHEMA,
        "inventory": {"commit": inventory_sha or "WORKTREE", "target_commit": TARGET_INVENTORY_SHA},
        "tool": {
            "python": platform.python_implementation() + " " + platform.python_version(),
            "pytest": pytest.__version__, "pyyaml": importlib.metadata.version("PyYAML"),
            "normalization": ["JSON mapping-key ordering", "explicit set-like field sorting only", "absolute temporary roots -> <TEMP_ROOT>"],
        },
        "config": config, "source_parse_errors": parse_errors,
        "test_files": test_files,
        "zero_function_files": sorted(path for path in test_files if path not in unit_paths),
        "source_units": compact_rows, "collection": _compact_collection(collection),
        "reconciliation": reconciliation, "manifests": manifests,
        "ownership": {"unowned": sorted(set(unowned)), "complete": not unowned},
        "empty_tests_root": not test_files,
    }
    evidence["content_sha256"] = _sha(_json_bytes(evidence))
    return cast(dict[str, Any], _stable(evidence))


def _keys(row: Mapping[str, Any], fields: Iterable[str], where: str, errors: list[str]) -> None:
    for field in fields:
        if field not in row:
            errors.append(f"{where}: missing field {field}")


def _str_list(value: Any, *, nonempty: bool = False) -> bool:
    return isinstance(value, list) and (not nonempty or bool(value)) and all(isinstance(item, str) for item in value)


def _hash_value(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _enum_string(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def validate_environment(env: Mapping[str, Any], where: str, errors: list[str]) -> None:
    required = (
        "id", "os", "runner_image", "cpu_class", "python", "event", "env", "lock_hash",
        "install_command", "install_state", "workers", "cache_policy", "harness_patch_hash",
    )
    _keys(env, required, where, errors)
    scalar_fields = ("id", "os", "runner_image", "cpu_class", "python", "event", "lock_hash", "install_state", "workers", "cache_policy")
    if any(not _nonempty_string(env.get(field)) for field in scalar_fields):
        errors.append(f"{where}: scalar environment fields must be nonempty strings")
    env_map = env.get("env")
    if not isinstance(env_map, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env_map.items()):
        errors.append(f"{where}: env must be string mapping")
    if not _str_list(env.get("install_command"), nonempty=True):
        errors.append(f"{where}: install_command must be nonempty string list")
    if not _enum_string(env.get("event"), {"local", "PR", "push", "schedule", "manual"}):
        errors.append(f"{where}: invalid event")
    if not _hash_value(env.get("lock_hash")):
        errors.append(f"{where}: lock_hash must be SHA-256")
    harness_hash = env.get("harness_patch_hash")
    if harness_hash is not None and not _hash_value(harness_hash):
        errors.append(f"{where}: harness_patch_hash must be SHA-256 or null")
    body = {key: env.get(key) for key in required if key != "id"}
    if env.get("id") != _sha(_json_bytes(body)):
        errors.append(f"{where}: id is not SHA-256 of normalized environment fields")


def validate_route(
    route: Mapping[str, Any], where: str, errors: list[str],
    route_authority: Mapping[str, Mapping[str, Any]],
) -> None:
    _keys(route, ("route_id", "role", "required", "events", "selector"), where, errors)
    if not _enum_string(route.get("role"), ROUTE_ROLES):
        errors.append(f"{where}: invalid route role")
    if not isinstance(route.get("required"), bool):
        errors.append(f"{where}: required must be boolean")
    route_id = route.get("route_id")
    selector = route.get("selector")
    if not _nonempty_string(route_id) or not _str_list(route.get("events")) or not isinstance(selector, dict):
        errors.append(f"{where}: route_id must be nonempty string, events string list, and selector mapping")
        return
    route_id_string = cast(str, route_id)
    authority = route_authority.get(route_id_string)
    if authority is None:
        errors.append(f"{where}: unknown frozen route_id {route_id_string}")
    selector_fields = ("paths", "markers", "ignores", "environment_id")
    _keys(selector, selector_fields, f"{where}.selector", errors)
    if any(not _str_list(selector.get(field)) for field in ("paths", "markers", "ignores")):
        errors.append(f"{where}.selector: paths, markers, and ignores must be string lists")
    selector_environment = selector.get("environment_id")
    if not _nonempty_string(selector_environment):
        errors.append(f"{where}.selector: environment_id must be nonempty string")
    elif authority is not None and selector_environment != authority.get("environment_id"):
        errors.append(f"{where}.selector: environment_id does not match frozen route")


def _validate_result_field(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("result",), where, errors)
    if not _nonempty_string(row.get("result")):
        errors.append(f"{where}: result must be nonempty string")


def _validate_command_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("command", "result"), where, errors)
    command = row.get("command")
    if not (_nonempty_string(command) or _str_list(command, nonempty=True)):
        errors.append(f"{where}: command must be nonempty string or argv list")
    _validate_result_field(row, where, errors)


def _validate_authority_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("reference", "result"), where, errors)
    if not _nonempty_string(row.get("reference")):
        errors.append(f"{where}: reference must be nonempty string")
    _validate_result_field(row, where, errors)


def _validate_overlap_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("left", "right", "result"), where, errors)
    if not _nonempty_string(row.get("left")) or not _nonempty_string(row.get("right")):
        errors.append(f"{where}: left/right identities must be nonempty strings")
    _validate_result_field(row, where, errors)


def _validate_named_result_mapping(value: Any, where: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{where}: mapping required")
        return
    _keys(value, ("identity", "result"), where, errors)
    if not _nonempty_string(value.get("identity")):
        errors.append(f"{where}: identity must be nonempty string")
    _validate_result_field(value, where, errors)


def validate_causal_probe(probe: Any, where: str, errors: list[str]) -> None:
    if not isinstance(probe, dict):
        errors.append(f"{where}: causal_probe must be mapping")
        return
    fields = (
        "kind", "fault", "authority_violated", "act_reached", "intended_oracle",
        "intended_oracle_failed", "command", "environment", "raw_artifact_hash",
    )
    _keys(probe, fields, where, errors)
    if any(not _nonempty_string(probe.get(field)) for field in ("kind", "fault", "authority_violated", "intended_oracle", "command", "environment")):
        errors.append(f"{where}: causal text fields must be nonempty strings")
    if not _hash_value(probe.get("raw_artifact_hash")):
        errors.append(f"{where}: raw_artifact_hash must be SHA-256")
    if probe.get("act_reached") is not True or probe.get("intended_oracle_failed") is not True:
        errors.append(f"{where}: causal proof must reach Act and fail intended oracle")


def validate_workload(dag: Mapping[str, Any], where: str, errors: list[str], environment_ids: set[str]) -> None:  # noqa: C901 - schema branches are intentionally explicit
    _keys(dag, ("routes", "edges", "repetitions", "measurements"), where, errors)
    routes = dag.get("routes", [])
    edges = dag.get("edges", [])
    if not isinstance(routes, list) or not isinstance(edges, list) or not isinstance(dag.get("measurements"), list):
        errors.append(f"{where}: routes, edges, and measurements must be lists")
        return
    if not isinstance(dag.get("repetitions"), int) or dag.get("repetitions", 0) < 3:
        errors.append(f"{where}: repetitions must be >= 3")
    route_ids: set[str] = set()
    route_environments: dict[str, str] = {}
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"{where}.routes[{index}]: mapping required")
            continue
        route_where = f"{where}.routes[{index}]"
        _keys(route, ("id", "argv", "environment_id", "base_mapping", "head_mapping", "cwd", "env"), route_where, errors)
        route_id = route.get("id")
        if not _nonempty_string(route_id):
            errors.append(f"{route_where}: id must be nonempty string")
            continue
        route_id_string = cast(str, route_id)
        if route_id_string in route_ids:
            errors.append(f"{route_where}: duplicate route id {route_id_string}")
        route_ids.add(route_id_string)
        if not _str_list(route.get("argv"), nonempty=True):
            errors.append(f"{route_where}: argv must be nonempty string list")
        route_env = route.get("env")
        if (
            not _nonempty_string(route.get("cwd"))
            or not isinstance(route_env, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in route_env.items())
        ):
            errors.append(f"{route_where}: nonempty cwd/string env mapping required")
        route_environment = route.get("environment_id")
        if not isinstance(route_environment, str) or route_environment not in environment_ids:
            errors.append(f"{route_where}: unknown environment_id")
        elif isinstance(route_environment, str):
            route_environments[route_id_string] = route_environment
        if not _nonempty_string(route.get("base_mapping")) or not _nonempty_string(route.get("head_mapping")):
            errors.append(f"{route_where}: base/head mappings must be nonempty strings")
    graph: dict[Any, set[Any]] = {route_id: set() for route_id in route_ids}
    edge_ids: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict) or set(edge) < {"from", "to"}:
            errors.append(f"{where}.edges[{index}]: from/to required")
            continue
        edge_from, edge_to = edge.get("from"), edge.get("to")
        if not isinstance(edge_from, str) or not isinstance(edge_to, str):
            errors.append(f"{where}.edges[{index}]: from/to strings required")
            continue
        if edge_from not in route_ids or edge_to not in route_ids:
            errors.append(f"{where}.edges[{index}]: unknown route")
        edge_id = (edge_from, edge_to)
        if edge_id in edge_ids:
            errors.append(f"{where}.edges[{index}]: duplicate dependency edge {edge_from}->{edge_to}")
        edge_ids.add(edge_id)
        graph.setdefault(edge_from, set()).add(edge_to)
    visiting: set[Any] = set()
    visited: set[Any] = set()
    def visit(node: Any) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        if not all(visit(child) for child in graph.get(node, set())):
            return False
        visiting.remove(node)
        visited.add(node)
        return True
    if not all(visit(node) for node in route_ids):
        errors.append(f"{where}: dependency graph is cyclic")
    for index, measurement in enumerate(dag.get("measurements", [])):
        if not isinstance(measurement, dict):
            errors.append(f"{where}.measurements[{index}]: mapping required")
            continue
        measurement_where = f"{where}.measurements[{index}]"
        fields = ("route_id", "environment_id", "collection", "setup", "call", "wall", "compute", "outcome", "artifact_hash")
        _keys(measurement, fields, measurement_where, errors)
        measurement_route = measurement.get("route_id")
        measurement_environment = measurement.get("environment_id")
        if not _nonempty_string(measurement_route) or measurement_route not in route_ids:
            errors.append(f"{measurement_where}: unknown route_id")
        if not _nonempty_string(measurement_environment) or measurement_environment not in environment_ids:
            errors.append(f"{measurement_where}: unknown environment_id")
        if (
            isinstance(measurement_route, str)
            and isinstance(measurement_environment, str)
            and route_environments.get(measurement_route) != measurement_environment
        ):
            errors.append(f"{measurement_where}: environment_id does not match route")
        if any(not _nonnegative_number(measurement.get(field)) for field in ("collection", "setup", "call", "wall", "compute")):
            errors.append(f"{measurement_where}: timing fields must be finite nonnegative numbers")
        if not _enum_string(measurement.get("outcome"), MEASUREMENT_OUTCOMES):
            errors.append(f"{measurement_where}: invalid outcome")
        if not _hash_value(measurement.get("artifact_hash")):
            errors.append(f"{measurement_where}: artifact_hash must be SHA-256")


def validate_census(data: Mapping[str, Any], errors: list[str]) -> None:  # noqa: C901 - fail-closed compact schema matrix
    if data.get("schema_version") != SCHEMA:
        errors.append("census: schema_version must be test-sanitation/v1")
    reconciliation = data.get("reconciliation", {})
    if not isinstance(reconciliation, dict):
        errors.append("census: reconciliation mapping required")
        return
    if not reconciliation.get("complete"):
        errors.append("census: discovery/collection reconciliation incomplete")
    if reconciliation.get("unreconciled_or_duplicate_nodes"):
        errors.append("census: node membership is missing or duplicated")
    if not data.get("ownership", {}).get("complete"):
        errors.append("census: candidate/group owner reconciliation incomplete")
    inventory = data.get("inventory", {})
    if not isinstance(inventory, dict) or inventory.get("commit") != TARGET_INVENTORY_SHA or inventory.get("target_commit") != TARGET_INVENTORY_SHA:
        errors.append("census: immutable inventory and target commits must match target SHA")
    if data.get("source_parse_errors"):
        errors.append("census: source parse errors require explicit repair before inventory")
    units = data.get("source_units", [])
    collection = data.get("collection", {})
    if not isinstance(units, list) or not isinstance(collection, dict):
        errors.append("census: source_units list and collection mapping required")
        return
    test_files = data.get("test_files")
    zero_function_files = data.get("zero_function_files")
    if not _str_list(test_files) or not _str_list(zero_function_files):
        errors.append("census: test_files and zero_function_files must be string lists")
    elif not set(cast(list[str], zero_function_files)) <= set(cast(list[str], test_files)):
        errors.append("census: zero_function_files must reference test_files")
    elif data.get("empty_tests_root") is not (test_files == []):
        errors.append("census: empty_tests_root inconsistent with discovered files")
    if collection.get("exit_code") not in {0, 5} or collection.get("internal_errors") or collection.get("collection_errors"):
        errors.append("census: collection exited nonzero or recorded collection/internal errors")
    states = [row.get("collection_state") for row in units if isinstance(row, dict)]
    if not all(_enum_string(state, COLLECTION_STATES) for state in states):
        errors.append("census: invalid collection_state")
    if len(units) != reconciliation.get("source_units"):
        errors.append("census: source unit count mismatch")
    actual_states = {state: sum(isinstance(row, dict) and row.get("collection_state") == state for row in units) for state in sorted(COLLECTION_STATES)}
    if actual_states != reconciliation.get("state_counts"):
        errors.append("census: state counts do not match source rows")
    tables = collection.get("tables", {})
    nodes = collection.get("nodes", [])
    expected_fields = ["nodeid", "path_ref", "line", "parent_source_function_ref", "marker_set_ref", "quarantined", "reason_ref"]
    if collection.get("node_fields") != expected_fields or not isinstance(tables, dict) or not isinstance(nodes, list):
        errors.append("census: invalid compact collection schema")
        nodes = []
        tables = {}
    paths = tables.get("paths", []) if isinstance(tables, dict) else []
    functions = tables.get("parent_source_functions", []) if isinstance(tables, dict) else []
    marker_sets = tables.get("marker_sets", []) if isinstance(tables, dict) else []
    reasons = tables.get("reasons", []) if isinstance(tables, dict) else []
    nodeids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, list) or len(node) != len(expected_fields):
            errors.append(f"census: node[{index}] row width/type invalid")
            continue
        nodeid, path_ref, line, function_ref, marker_ref, quarantined, reason_ref = node
        if not isinstance(nodeid, str) or nodeid in nodeids:
            errors.append(f"census: node[{index}] nodeid missing/duplicate")
        nodeids.add(nodeid)
        refs_valid = (
            isinstance(path_ref, int) and 0 <= path_ref < len(paths)
            and isinstance(function_ref, int) and 0 <= function_ref < len(functions)
            and isinstance(marker_ref, int) and 0 <= marker_ref < len(marker_sets)
            and (reason_ref is None or isinstance(reason_ref, int) and 0 <= reason_ref < len(reasons))
        )
        if not refs_valid or not isinstance(line, int) or not isinstance(quarantined, bool):
            errors.append(f"census: node[{index}] invalid compact reference/type")
    if len(nodes) != reconciliation.get("collected_nodes"):
        errors.append("census: collected node count mismatch")
    membership = [0] * len(nodes)
    source_ids: set[str] = set()
    for index, row in enumerate(units):
        if not isinstance(row, dict):
            errors.append(f"census: source_units[{index}] mapping required")
            continue
        source_id = row.get("id")
        if not isinstance(source_id, str) or source_id in source_ids:
            errors.append(f"census: source_units[{index}] id missing/duplicate")
        if isinstance(source_id, str):
            source_ids.add(source_id)
        if (
            not isinstance(row.get("path"), str)
            or not isinstance(row.get("qualname"), str)
            or not isinstance(row.get("line"), int)
            or not _str_list(row.get("decorators"))
            or not _str_list(row.get("inert_reasons"))
            or not _hash_value(row.get("exact_body_sha256"))
            or not _hash_value(row.get("structural_shape_sha256"))
            or not isinstance(row.get("zero_node"), bool)
        ):
            errors.append(f"census: source_units[{index}] typed fields invalid")
        refs = row.get("node_refs")
        if not isinstance(refs, list):
            errors.append(f"census: source_units[{index}] node_refs list required")
            continue
        if row.get("collection_state") == "collected" and not refs:
            errors.append(f"census: collected source_units[{index}] has no nodes")
        if row.get("collection_state") != "collected" and refs:
            errors.append(f"census: non-collected source_units[{index}] has node refs")
        for ref in refs:
            if not isinstance(ref, int) or not 0 <= ref < len(nodes):
                errors.append(f"census: source_units[{index}] invalid node ref")
            else:
                membership[ref] += 1
    if any(count != 1 for count in membership):
        errors.append("census: every collection node must have exactly one source membership")
    ownership = data.get("ownership", {})
    if not isinstance(ownership, dict) or not isinstance(ownership.get("unowned"), list):
        errors.append("census: ownership mapping/unowned list required")
    elif ownership.get("complete") is not (ownership["unowned"] == []):
        errors.append("census: ownership.complete inconsistent with unowned list")
    expected = data.get("content_sha256")
    body = dict(data)
    body.pop("content_sha256", None)
    if expected != _sha(_json_bytes(body)):
        errors.append("census: content_sha256 mismatch")


def _validate_temporary(row: Mapping[str, Any], where: str, profile: Any, today: dt.date, errors: list[str]) -> None:
    _keys(row, ("hic_approval", "issue", "owner", "expires"), where, errors)
    if profile != "environmental_platform":
        errors.append(f"{where}: TEMPORARY only permits environmental_platform")
    for field in ("hic_approval", "issue", "owner", "expires"):
        if not _nonempty_string(row.get(field)):
            errors.append(f"{where}: TEMPORARY {field} must be nonempty string")
    renewal = row.get("renewal", False)
    if not isinstance(renewal, bool):
        errors.append(f"{where}: TEMPORARY renewal must be boolean")
    elif renewal:
        errors.append(f"{where}: TEMPORARY cannot renew")
    expires = row.get("expires")
    if not isinstance(expires, str):
        return
    try:
        expiry = dt.date.fromisoformat(expires)
        if expiry < today or expiry > today + dt.timedelta(days=30):
            errors.append(f"{where}: TEMPORARY expiry must be today..today+30d")
    except ValueError:
        errors.append(f"{where}: invalid TEMPORARY expiry")


def _validate_evidence(  # noqa: C901 - each EvidenceBundle field has a distinct nested schema
    evidence: Mapping[str, Any], where: str, errors: list[str],
    route_authority: Mapping[str, Mapping[str, Any]], candidate_route_roles: Mapping[str, str],
) -> Any:
    _keys(evidence, ("profile",), where, errors)
    profile = evidence.get("profile")
    if not _enum_string(profile, PROFILES):
        errors.append(f"{where}: invalid evidence profile {profile!r}")
    list_fields = ("caller_evidence", "authority_evidence", "routing_evidence", "overlap_evidence")
    for field in list_fields:
        value = evidence.get(field)
        if field in evidence and (
            not isinstance(value, list) or not all(isinstance(item, dict) for item in value)
        ):
            errors.append(f"{where}.{field}: list of mapping evidence rows required")
    for field in ("base_evidence", "cost_evidence"):
        if field in evidence:
            _validate_named_result_mapping(evidence.get(field), f"{where}.{field}", errors)
    if "causal_probe" in evidence and not isinstance(evidence.get("causal_probe"), dict):
        errors.append(f"{where}.causal_probe: mapping required")
    requirements = {
        "inert": ("routing_evidence", "authority_evidence"),
        "duplicate": ("overlap_evidence", "causal_probe"),
        "structural": ("authority_evidence", "causal_probe"),
        "contract": ("caller_evidence", "authority_evidence", "causal_probe"),
        "slow": ("cost_evidence", "causal_probe"),
        "flake": ("base_evidence",),
        "dead_symbol": ("caller_evidence", "authority_evidence"),
        "route": ("routing_evidence", "cost_evidence"),
        "environmental_platform": ("base_evidence", "routing_evidence"),
    }
    required_fields = requirements.get(profile, ()) if isinstance(profile, str) else ()
    for field in required_fields:
        value = evidence.get(field)
        if field not in evidence or value in (None, [], {}):
            errors.append(f"{where}[{profile}]: nonempty {field} required")
    validators = {
        "caller_evidence": _validate_command_evidence,
        "authority_evidence": _validate_authority_evidence,
        "overlap_evidence": _validate_overlap_evidence,
    }
    for field, validator in validators.items():
        rows = evidence.get(field)
        if not isinstance(rows, list):
            continue
        for row_index, nested_row in enumerate(rows):
            if isinstance(nested_row, dict):
                validator(nested_row, f"{where}.{field}[{row_index}]", errors)
    routing_rows = evidence.get("routing_evidence")
    if isinstance(routing_rows, list):
        for row_index, nested_row in enumerate(routing_rows):
            if not isinstance(nested_row, dict):
                continue
            row_where = f"{where}.routing_evidence[{row_index}]"
            validate_route(nested_row, row_where, errors, route_authority)
            _validate_result_field(nested_row, row_where, errors)
            route_id = nested_row.get("route_id")
            role = nested_row.get("role")
            if isinstance(route_id, str) and route_id not in candidate_route_roles:
                errors.append(f"{row_where}: route_id is not a candidate RouteMembership")
            elif isinstance(route_id, str) and role != candidate_route_roles.get(route_id):
                errors.append(f"{row_where}: role does not match candidate RouteMembership")
    if "causal_probe" in evidence:
        validate_causal_probe(evidence.get("causal_probe"), f"{where}.causal_probe", errors)
    return profile


def _validate_family(  # noqa: C901 - family anti-vacuity matrix is intentionally explicit
    candidate: Mapping[str, Any], members: list[str], observations: list[Any], where: str,
    census_members: set[str], errors: list[str],
) -> None:
    dimensions_value = candidate.get("equivalence")
    if not isinstance(dimensions_value, dict):
        errors.append(f"{where}: family equivalence dimensions mapping required")
        dimensions: Mapping[str, Any] = {}
    else:
        dimensions = dimensions_value
    missing_dimensions = EQUIVALENCE_DIMENSIONS - set(dimensions)
    if missing_dimensions:
        errors.append(f"{where}: family equivalence dimensions missing {sorted(missing_dimensions)}")
    for dimension in EQUIVALENCE_DIMENSIONS:
        if dimension in dimensions and not _nonempty_string(dimensions.get(dimension)):
            errors.append(f"{where}: equivalence.{dimension} must be nonempty string")

    divergent_value = candidate.get("divergent_dimensions", [])
    if not _str_list(divergent_value):
        errors.append(f"{where}: divergent_dimensions must be string list")
        divergent: list[str] = []
    else:
        divergent = cast(list[str], divergent_value)
        if len(divergent) != len(set(divergent)):
            errors.append(f"{where}: divergent_dimensions must be unique")
        unknown = set(divergent) - EQUIVALENCE_DIMENSIONS
        if unknown:
            errors.append(f"{where}: unknown divergent dimensions {sorted(unknown)}")

    observation_rows = [obs for obs in observations if isinstance(obs, dict)]
    observed_dimensions: set[str] = set()
    if len({repr(obs.get("outcome")) for obs in observation_rows}) > 1:
        observed_dimensions.add("outcome")
    if len({
        repr(obs.get("duration", {}).get("cost_class"))
        for obs in observation_rows if isinstance(obs.get("duration"), dict)
    }) > 1:
        observed_dimensions.add("cost_class")
    if not observed_dimensions <= set(divergent):
        errors.append(f"{where}: observed divergent dimensions must be declared")

    node_rows_value = candidate.get("node_rows")
    has_divergence = bool(divergent or observed_dimensions)
    if node_rows_value is None:
        if has_divergence:
            errors.append(f"{where}: divergent family dimensions require nonempty node_rows")
        return
    if not isinstance(node_rows_value, list):
        errors.append(f"{where}: node_rows must be list")
        return
    if has_divergence and not node_rows_value:
        errors.append(f"{where}: divergent family dimensions require nonempty node_rows")
        return

    row_members: list[str] = []
    row_dimensions: dict[str, list[str]] = {dimension: [] for dimension in EQUIVALENCE_DIMENSIONS}
    for row_index, node_row in enumerate(node_rows_value):
        row_where = f"{where}.node_rows[{row_index}]"
        if not isinstance(node_row, dict):
            errors.append(f"{row_where}: mapping required")
            continue
        _keys(node_row, ("member", *sorted(EQUIVALENCE_DIMENSIONS)), row_where, errors)
        member = node_row.get("member")
        if not _nonempty_string(member):
            errors.append(f"{row_where}: member must be nonempty string")
        else:
            member_string = cast(str, member)
            row_members.append(member_string)
            if member_string not in members or member_string not in census_members:
                errors.append(f"{row_where}: member must reference candidate and census identity")
        for dimension in EQUIVALENCE_DIMENSIONS:
            value = node_row.get(dimension)
            if not _nonempty_string(value):
                errors.append(f"{row_where}: {dimension} must be nonempty string")
            else:
                row_dimensions[dimension].append(cast(str, value))
    if len(row_members) != len(set(row_members)):
        errors.append(f"{where}: node_rows contain duplicate member identities")
    if set(row_members) != set(members) or len(row_members) != len(members):
        errors.append(f"{where}: node_rows must cover every candidate member exactly once")
    for dimension, values in row_dimensions.items():
        if len(values) != len(members):
            continue
        if dimension in divergent:
            if len(set(values)) < 2:
                errors.append(f"{where}: divergent dimension {dimension} must vary across node_rows")
        elif dimension in dimensions and any(value != dimensions[dimension] for value in values):
            errors.append(f"{where}: node_rows disagree with equivalence.{dimension}")


def validate_disposition(  # noqa: C901 - fail-closed schema matrix
    row: Mapping[str, Any], index: int, today: dt.date, errors: list[str],
    census_members: set[str], environment_ids: set[str], census_nodes: set[str],
    census_member_nodes: Mapping[str, set[str]], census_member_states: Mapping[str, str],
    route_authority: Mapping[str, Mapping[str, Any]],
) -> None:
    where = f"dispositions[{index}]"
    _keys(row, ("candidate", "evidence", "verdict", "state", "action", "survivor", "issue", "owner", "expires", "hic_approval", "review"), where, errors)
    verdict, state = row.get("verdict"), row.get("state")
    if not _enum_string(verdict, VERDICTS):
        errors.append(f"{where}: unknown verdict {verdict!r}")
    if state == "terminal" and isinstance(verdict, str) and verdict in {"FIX_TEST", "FIX_PRODUCT"}:
        errors.append(f"{where}: FIX_* cannot be terminal")
    if not _enum_string(state, {"pending", "terminal"}):
        errors.append(f"{where}: state must be pending or terminal")
    if not _nonempty_string(row.get("action")):
        errors.append(f"{where}: action must be nonempty string")
    if row.get("survivor") is not None and not isinstance(row.get("survivor"), str):
        errors.append(f"{where}: survivor must be string or null")
    for field in ("issue", "owner", "expires", "hic_approval"):
        if row.get(field) is not None and not isinstance(row.get(field), str):
            errors.append(f"{where}: {field} must be string or null")
    candidate_value = row.get("candidate", {})
    evidence_value = row.get("evidence", {})
    if not isinstance(candidate_value, dict):
        errors.append(f"{where}.candidate: mapping required")
        candidate: Mapping[str, Any] = {}
    else:
        candidate = candidate_value
    if not isinstance(evidence_value, dict):
        errors.append(f"{where}.evidence: mapping required")
        evidence: Mapping[str, Any] = {}
    else:
        evidence = evidence_value
    candidate_fields = (
        "id", "members", "granularity", "source_paths", "production_paths", "oracle", "contract_claim",
        "authority", "duplicate_group", "route_memberships", "platforms", "observations",
    )
    _keys(candidate, candidate_fields, f"{where}.candidate", errors)
    if not _nonempty_string(candidate.get("id")):
        errors.append(f"{where}: candidate id must be nonempty string")
    members_value = candidate.get("members")
    if not _str_list(members_value, nonempty=True):
        errors.append(f"{where}: members must be nonempty string list")
        candidate_members: list[str] = []
    else:
        candidate_members = cast(list[str], members_value)
    for member in candidate_members:
        if member not in census_members:
            errors.append(f"{where}: stale/unknown census member {member}")
    for field in ("source_paths", "production_paths", "authority", "platforms"):
        value = candidate.get(field)
        if field in candidate and not _str_list(value, nonempty=field in {"source_paths", "platforms"}):
            errors.append(f"{where}: {field} must be string list")
    for field in ("oracle", "contract_claim", "duplicate_group"):
        if candidate.get(field) is not None and not isinstance(candidate.get(field), str):
            errors.append(f"{where}: {field} must be string or null")
    if not _enum_string(candidate.get("granularity"), GRANULARITIES):
        errors.append(f"{where}: invalid granularity")
    memberships = candidate.get("route_memberships", [])
    if not isinstance(memberships, list):
        errors.append(f"{where}.route_memberships: list required")
        memberships = []
    candidate_route_roles: dict[str, str] = {}
    for route_index, route in enumerate(memberships):
        if isinstance(route, dict):
            validate_route(route, f"{where}.routes[{route_index}]", errors, route_authority)
            route_id = route.get("route_id")
            role = route.get("role")
            if isinstance(route_id, str) and isinstance(role, str):
                if route_id in candidate_route_roles:
                    errors.append(f"{where}.routes[{route_index}]: duplicate candidate route_id {route_id}")
                else:
                    candidate_route_roles[route_id] = role
        else:
            errors.append(f"{where}.routes[{route_index}]: mapping required")
    if sum(isinstance(item, dict) and item.get("role") == "owner" for item in memberships) != 1:
        errors.append(f"{where}: exactly one owner route required")
    profile = _validate_evidence(
        evidence, f"{where}.evidence", errors, route_authority, candidate_route_roles,
    )
    allowed_candidate_nodes: set[str] = set()
    for member in candidate_members:
        allowed_candidate_nodes.update(census_member_nodes.get(member, set()))
    observations = candidate.get("observations", [])
    if not isinstance(observations, list):
        errors.append(f"{where}.observations: list required")
        observations = []
    elif not observations:
        errors.append(f"{where}.observations: at least one observation required")
    for obs_index, obs in enumerate(observations):
        if not isinstance(obs, dict):
            errors.append(f"{where}.observations[{obs_index}]: mapping required")
            continue
        collection_state = obs.get("collection_state")
        outcome = obs.get("outcome")
        if not _enum_string(collection_state, COLLECTION_STATES) or not (
            outcome is None or _enum_string(outcome, cast(set[str], OUTCOMES - {None}))
        ):
            errors.append(f"{where}.observations[{obs_index}]: invalid state/outcome")
        observation_fields = (
            "environment_id", "nodeid", "collection_state", "outcome", "skip_reason",
            "markers", "duration", "artifact_hash",
        )
        _keys(obs, observation_fields, f"{where}.observations[{obs_index}]", errors)
        if not isinstance(obs.get("environment_id"), str) or obs.get("environment_id") not in environment_ids:
            errors.append(f"{where}.observations[{obs_index}]: unknown environment_id")
        if obs.get("nodeid") is not None and not isinstance(obs.get("nodeid"), str):
            errors.append(f"{where}.observations[{obs_index}]: nodeid must be string/null")
        observation_nodeid = obs.get("nodeid")
        if isinstance(observation_nodeid, str):
            if observation_nodeid not in census_nodes:
                errors.append(f"{where}.observations[{obs_index}]: nodeid absent from census")
            if observation_nodeid not in allowed_candidate_nodes:
                errors.append(f"{where}.observations[{obs_index}]: nodeid does not belong to candidate members")
            if not _enum_string(collection_state, {"collected", "deselected"}):
                errors.append(f"{where}.observations[{obs_index}]: non-null nodeid requires collected/deselected state")
        elif observation_nodeid is None:
            if not _enum_string(collection_state, {"zero_node", "ignored", "error"}):
                errors.append(f"{where}.observations[{obs_index}]: nodeid null only for source-only states")
            elif not any(census_member_states.get(member) == collection_state for member in candidate_members):
                errors.append(f"{where}.observations[{obs_index}]: null node state does not match candidate source state")
        if obs.get("skip_reason") is not None and not isinstance(obs.get("skip_reason"), str):
            errors.append(f"{where}.observations[{obs_index}]: skip_reason must be string/null")
        if not _str_list(obs.get("markers")) or not _hash_value(obs.get("artifact_hash")):
            errors.append(f"{where}.observations[{obs_index}]: markers/string list and SHA artifact required")
        duration = obs.get("duration")
        if not isinstance(duration, dict) or not {"collection", "setup", "call", "cost_class"} <= set(duration):
            errors.append(f"{where}.observations[{obs_index}]: typed duration fields required")
        elif any(not _nonnegative_number(duration.get(phase)) for phase in ("collection", "setup", "call")) or not _nonempty_string(duration.get("cost_class")):
            errors.append(f"{where}.observations[{obs_index}]: invalid duration values")
        markers = obs.get("markers")
        skip_like = isinstance(outcome, str) and outcome in {"skipped", "xfailed"}
        quarantined = isinstance(markers, list) and "quarantine" in markers
        if (skip_like or quarantined) and not obs.get("skip_reason"):
            errors.append(f"{where}.observations[{obs_index}]: skip_reason required")
    if verdict == "KEEP":
        if not _str_list(candidate.get("production_paths"), nonempty=True):
            errors.append(f"{where}.KEEP: nonempty production_paths required")
        if not _str_list(candidate.get("authority"), nonempty=True):
            errors.append(f"{where}.KEEP: nonempty authority required")
        if not _nonempty_string(candidate.get("oracle")) or not _nonempty_string(candidate.get("contract_claim")):
            errors.append(f"{where}.KEEP: nonempty oracle and contract_claim required")
        validate_causal_probe(evidence.get("causal_probe"), f"{where}.KEEP.causal_probe", errors)
    if verdict == "CONSOLIDATE" and state == "terminal":
        survivor = row.get("survivor")
        if not _nonempty_string(survivor):
            errors.append(f"{where}: terminal consolidation requires nonempty survivor")
        elif cast(str, survivor) not in candidate_members:
            errors.append(f"{where}: survivor must reference candidate member")
        if len(candidate_members) < 2:
            errors.append(f"{where}: terminal consolidation needs deleted and surviving members")
    if verdict == "TEMPORARY":
        _validate_temporary(row, where, profile, today, errors)
    review = row.get("review", {})
    if isinstance(review, dict):
        review_fields = ("implementer", "independent_reviewer", "verdict", "timestamp")
        _keys(review, review_fields, f"{where}.review", errors)
        if any(not _nonempty_string(review.get(field)) for field in review_fields):
            errors.append(f"{where}.review: fields must be nonempty strings")
        try:
            dt.datetime.fromisoformat(str(review.get("timestamp")).replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{where}.review: invalid timestamp")
    else:
        errors.append(f"{where}.review: mapping required")
    if isinstance(candidate.get("granularity"), str) and candidate.get("granularity") in {"family", "duplicate_cluster"}:
        _validate_family(candidate, candidate_members, observations, where, census_members, errors)


def _collect_census_authority(  # noqa: C901 - compact collected/deselected authority has distinct forms
    data: Mapping[str, Any], census_members: set[str], census_nodes: set[str],
    member_nodes: dict[str, set[str]], member_states: dict[str, str],
) -> None:
    collection = data.get("collection", {})
    if not isinstance(collection, dict):
        return
    compact_nodes = collection.get("nodes", [])
    if not isinstance(compact_nodes, list):
        compact_nodes = []
    nodeids_by_ref: list[str | None] = []
    for compact_row in compact_nodes:
        nodeid = compact_row[0] if isinstance(compact_row, list) and compact_row and isinstance(compact_row[0], str) else None
        nodeids_by_ref.append(nodeid)
        if nodeid is not None:
            census_nodes.add(nodeid)
            census_members.add(nodeid)
            member_nodes[nodeid] = {nodeid}
            member_states[nodeid] = "collected"
    deselected_by_source: dict[tuple[str, str], set[str]] = {}
    deselected_items = collection.get("deselected_items", [])
    if isinstance(deselected_items, list):
        for item in deselected_items:
            if not isinstance(item, dict):
                continue
            nodeid, path, source = item.get("nodeid"), item.get("path"), item.get("parent_source_function")
            if not all(isinstance(value, str) for value in (nodeid, path, source)):
                continue
            nodeid_string = cast(str, nodeid)
            census_nodes.add(nodeid_string)
            census_members.add(nodeid_string)
            member_nodes[nodeid_string] = {nodeid_string}
            member_states[nodeid_string] = "deselected"
            deselected_by_source.setdefault((cast(str, path), cast(str, source)), set()).add(nodeid_string)
    units = data.get("source_units", [])
    if not isinstance(units, list):
        return
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("id"), str):
            continue
        member = cast(str, unit["id"])
        census_members.add(member)
        resolved: set[str] = set()
        refs = unit.get("node_refs", [])
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, int) and 0 <= ref < len(nodeids_by_ref) and nodeids_by_ref[ref] is not None:
                    resolved.add(cast(str, nodeids_by_ref[ref]))
        path, qualname = unit.get("path"), unit.get("qualname")
        if isinstance(path, str) and isinstance(qualname, str):
            resolved.update(deselected_by_source.get((path, qualname), set()))
        member_nodes[member] = resolved
        state = unit.get("collection_state")
        if isinstance(state, str):
            member_states[member] = state


def _collect_route_authority(
    data: Mapping[str, Any], path: Path, route_authority: dict[str, Mapping[str, Any]],
    route_locations: dict[str, str], errors: list[str],
) -> None:
    workload = data.get("frozen_workload_dag")
    if not isinstance(workload, dict) or not isinstance(workload.get("routes"), list):
        return
    for route_index, route in enumerate(workload["routes"]):
        if not isinstance(route, dict) or not isinstance(route.get("id"), str):
            continue
        route_id = cast(str, route["id"])
        location = f"{path}.frozen_workload_dag.routes[{route_index}]"
        if route_id in route_locations:
            errors.append(f"{location}: duplicate global frozen route id {route_id}; first at {route_locations[route_id]}")
            continue
        route_locations[route_id] = location
        route_authority[route_id] = route


def validate_documents(paths: Sequence[Path], today: dt.date) -> tuple[list[str], dict[str, Any]]:  # noqa: C901 - heterogeneous document fail-closed dispatch
    errors: list[str] = []
    members: dict[str, str] = {}
    candidate_ids: dict[str, str] = {}
    loaded: list[str] = []
    documents: list[tuple[Path, dict[str, Any]]] = []
    disposition_count = 0
    for path in paths:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path}: cannot load: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: top-level mapping required")
            continue
        loaded.append(path.as_posix())
        documents.append((path, data))
    census_members: set[str] = set()
    census_nodes: set[str] = set()
    census_member_nodes: dict[str, set[str]] = {}
    census_member_states: dict[str, str] = {}
    environment_ids: set[str] = set()
    environment_locations: dict[str, str] = {}
    route_authority: dict[str, Mapping[str, Any]] = {}
    route_locations: dict[str, str] = {}
    for path, data in documents:
        if "source_units" in data and "reconciliation" in data:
            validate_census(data, errors)
            _collect_census_authority(
                data, census_members, census_nodes, census_member_nodes, census_member_states,
            )
        _collect_route_authority(data, path, route_authority, route_locations, errors)
        environments = data.get("run_environments", data.get("environments", []))
        if isinstance(environments, dict):
            environments = list(environments.values())
        if not isinstance(environments, list):
            errors.append("environments must be list or mapping")
            environments = []
        for env_index, env in enumerate(environments):
            if isinstance(env, dict) and isinstance(env.get("id"), str):
                env_id = env["id"]
                location = f"{path}.environments[{env_index}]"
                if env_id in environment_locations:
                    errors.append(f"{location}: duplicate environment id {env_id}; first at {environment_locations[env_id]}")
                else:
                    environment_locations[env_id] = location
                environment_ids.add(env_id)
    for path, data in documents:
        environments = data.get("run_environments", data.get("environments", []))
        if isinstance(environments, dict):
            environments = list(environments.values())
        if not isinstance(environments, list):
            environments = []
        for env_index, env in enumerate(environments):
            if isinstance(env, dict):
                validate_environment(env, f"{path}.environments[{env_index}]", errors)
            else:
                errors.append(f"{path}.environments[{env_index}]: mapping required")
        workload = data.get("frozen_workload_dag")
        if workload is not None:
            if isinstance(workload, dict):
                validate_workload(workload, f"{path}.frozen_workload_dag", errors, environment_ids)
            else:
                errors.append(f"{path}.frozen_workload_dag: mapping required")
        rows = data.get("dispositions", [])
        if not isinstance(rows, list):
            errors.append(f"{path}: dispositions must be list")
            continue
        if rows and data.get("schema_version") != SCHEMA:
            errors.append(f"{path}: schema_version must be {SCHEMA}")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{path}: dispositions[{index}] must be mapping")
                continue
            validate_disposition(
                row, index, today, errors, census_members, environment_ids, census_nodes,
                census_member_nodes, census_member_states, route_authority,
            )
            disposition_count += 1
            candidate = row.get("candidate", {})
            candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
            if isinstance(candidate_id, str):
                location = f"{path}: dispositions[{index}]"
                if candidate_id in candidate_ids:
                    errors.append(f"duplicate candidate id {candidate_id}: {candidate_ids[candidate_id]} and {location}")
                else:
                    candidate_ids[candidate_id] = location
            candidate_members = candidate.get("members", []) if isinstance(candidate, dict) else []
            if not isinstance(candidate_members, list):
                candidate_members = []
            for member in candidate_members:
                if not isinstance(member, str):
                    errors.append(f"{path}: candidate member must be string")
                    continue
                if member in members:
                    errors.append(f"duplicate deep membership {member}: {members[member]} and {path}")
                members[member] = path.as_posix()
    return sorted(errors), {"documents": loaded, "dispositions": disposition_count, "unique_members": len(members)}


def aggregate(paths: Sequence[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    source_files: list[dict[str, str]] = []
    for path in sorted(paths):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise AuditError(f"{path}: cannot load: {exc}") from exc
        if not isinstance(data, dict):
            raise AuditError(f"{path}: top-level mapping required")
        source_files.append({"path": path.as_posix(), "sha256": _sha(path.read_bytes())})
        dispositions = data.get("dispositions", [])
        if not isinstance(dispositions, list) or not all(isinstance(row, dict) for row in dispositions):
            raise AuditError(f"{path}: dispositions must be a list of mappings")
        for index, row in enumerate(cast(list[dict[str, Any]], dispositions)):
            if not isinstance(row.get("candidate"), dict):
                raise AuditError(f"{path}: dispositions[{index}].candidate must be mapping")
            rows.append(row)
    rows.sort(key=lambda row: str(cast(dict[str, Any], row["candidate"]).get("id", "")))
    result = {"schema_version": SCHEMA, "generated_from": source_files, "dispositions": rows}
    result["content_sha256"] = _sha(_json_bytes(result))
    return cast(dict[str, Any], _stable(result))


def selftest() -> dict[str, Any]:
    """Exercise anti-vacuity cases in disposable runtime fixture trees."""
    with tempfile.TemporaryDirectory(prefix="sanitation-audit-") as temporary:
        root = Path(temporary)
        tests = root / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text(
            "import pytest\n"
            "collect_ignore = ['test_static_ignore.py']\n"
            "def pytest_ignore_collect(collection_path, config):\n"
            "    return True if collection_path.name == 'test_dynamic_ignore.py' else None\n",
            encoding="utf-8",
        )
        (tests / "test_cases.py").write_text(
            "import pytest\n"
            "@pytest.mark.inherited\n"
            "@pytest.mark.selected\n"
            "class TestOne:\n"
            "    def test_same(self): assert True\n"
            "class TestTwo:\n"
            "    @pytest.mark.parametrize('value', [1, 2])\n"
            "    def test_same(self, value): assert value\n"
            "def test_duplicate_a(): assert 1 == 1\n"
            "def test_duplicate_b(): assert 1 == 1\n"
            "def factory():\n"
            "    def test_nested(): assert True\n"
            "    return test_nested\n",
            encoding="utf-8",
        )
        (tests / "helper.py").write_text("def test_zero_node(): assert True\n", encoding="utf-8")
        (tests / "test_static_ignore.py").write_text("def test_static(): assert True\n", encoding="utf-8")
        (tests / "test_dynamic_ignore.py").write_text("def test_dynamic(): assert True\n", encoding="utf-8")
        (tests / "test_error.py").write_text(
            "raise RuntimeError('planted collection error')\ndef test_error(): assert True\n", encoding="utf-8",
        )
        first = snapshot(root, "tests", [], "SELFTEST")
        second = snapshot(root, "tests", [], "SELFTEST")
        if _json_bytes(first) != _json_bytes(second):
            raise AuditError("selftest: identical snapshots differ")
        units = {row["id"]: row for row in first["source_units"]}
        one = units["tests/test_cases.py::TestOne.test_same"]
        two = units["tests/test_cases.py::TestTwo.test_same"]
        compact_collection = first["collection"]
        marker_sets = compact_collection["tables"]["marker_sets"]
        checks = {
            "byte_identical": True,
            "zero_node": units["tests/helper.py::test_zero_node"]["collection_state"] == "zero_node",
            "static_ignore": units["tests/test_static_ignore.py::test_static"]["collection_state"] == "ignored",
            "dynamic_ignore": units["tests/test_dynamic_ignore.py::test_dynamic"]["collection_state"] == "ignored",
            "collection_error": units["tests/test_error.py::test_error"]["collection_state"] == "error",
            "same_name_membership": len(one["node_refs"]) == 1 and len(two["node_refs"]) == 2,
            "inherited_marker": any(
                marker == "inherited"
                for node_ref in one["node_refs"]
                for marker in marker_sets[compact_collection["nodes"][node_ref][4]]
            ),
            "exact_duplicate": bool(first["manifests"]["exact_body_groups"]),
            "unowned_fails": first["ownership"]["complete"] is False,
            "recursive_nested_once": list(units).count("tests/test_cases.py::factory.test_nested") == 1,
        }
        selected = snapshot(root, "tests", ["-m", "selected", "--ignore=tests/test_error.py"], "SELFTEST-SELECT")
        selected_units = {row["id"]: row for row in selected["source_units"]}
        checks["deselected_class_parameter_family"] = (
            selected_units["tests/test_cases.py::TestTwo.test_same"]["collection_state"] == "deselected"
            and selected["reconciliation"]["state_counts"]["deselected"] >= 1
        )
        empty = root / "empty"
        (empty / "tests").mkdir(parents=True)
        empty_snapshot = snapshot(empty, "tests", [], "SELFTEST-EMPTY")
        checks["explicit_empty_census"] = (
            empty_snapshot["empty_tests_root"] is True
            and empty_snapshot["reconciliation"]["source_units"] == 0
            and empty_snapshot["collection"]["exit_code"] == 5
        )
        zero_file = root / "zero-file"
        (zero_file / "tests").mkdir(parents=True)
        (zero_file / "tests" / "test_empty.py").write_text("VALUE = 1\n", encoding="utf-8")
        zero_file_snapshot = snapshot(zero_file, "tests", [], "SELFTEST-ZERO-FILE")
        checks["zero_function_file_not_empty_root"] = (
            zero_file_snapshot["empty_tests_root"] is False
            and zero_file_snapshot["zero_function_files"] == ["tests/test_empty.py"]
        )
        for hook_name, hook_source in {
            "collection": "def pytest_collection(session): raise RuntimeError('collection crash')\n",
            "modifyitems": "def pytest_collection_modifyitems(session, config, items): raise RuntimeError('modify crash')\n",
        }.items():
            crash_root = root / f"crash-{hook_name}"
            (crash_root / "tests").mkdir(parents=True)
            (crash_root / "tests" / "conftest.py").write_text(hook_source, encoding="utf-8")
            (crash_root / "tests" / "test_case.py").write_text("def test_case(): assert True\n", encoding="utf-8")
            crashed = snapshot(crash_root, "tests", [], f"SELFTEST-{hook_name}")
            checks[f"{hook_name}_crash_fails_closed"] = (
                crashed["collection"]["exit_code"] not in {0, 5}
                and bool(crashed["collection"]["internal_errors"])
                and crashed["reconciliation"]["complete"] is False
            )
        shard = {
            "schema_version": SCHEMA,
            "dispositions": [{
                "candidate": {
                    "members": ["duplicate-member"], "granularity": "family",
                    "divergent_dimensions": ["outcome"],
                },
            }],
        }
        shard_a, shard_b = root / "a.yaml", root / "b.yaml"
        shard_a.write_text(yaml.safe_dump(shard), encoding="utf-8")
        shard_b.write_text(yaml.safe_dump(shard), encoding="utf-8")
        duplicate_errors, _ = validate_documents([shard_a, shard_b], dt.date.today())
        checks["duplicate_deep_membership_fails"] = any("duplicate deep membership" in error for error in duplicate_errors)
        checks["divergent_family_fails"] = any("divergent family dimensions require nonempty node_rows" in error for error in duplicate_errors)
        empty_shard = root / "empty-shard.yaml"
        empty_shard.write_text(yaml.safe_dump({"schema_version": SCHEMA, "dispositions": []}), encoding="utf-8")
        checks["aggregate_empty_shard"] = aggregate([empty_shard])["dispositions"] == []
        malformed = root / "malformed.yaml"
        malformed.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [{"candidate": "bad", "evidence": [], "verdict": "KEEP", "state": "terminal"}]}),
            encoding="utf-8",
        )
        malformed_errors, _ = validate_documents([malformed], dt.date.today())
        checks["malformed_shard_fails_without_crash"] = bool(malformed_errors)
        aggregate_bad = root / "aggregate-bad.yaml"
        aggregate_bad.write_text(yaml.safe_dump({"dispositions": "abc"}), encoding="utf-8")
        try:
            aggregate([aggregate_bad])
            checks["aggregate_malformed_controlled_error"] = False
        except AuditError:
            checks["aggregate_malformed_controlled_error"] = True
        aggregate_bad_candidate = root / "aggregate-bad-candidate.yaml"
        aggregate_bad_candidate.write_text(yaml.safe_dump({"dispositions": [{"candidate": "bad"}]}), encoding="utf-8")
        try:
            aggregate([aggregate_bad_candidate])
            checks["aggregate_malformed_candidate_controlled_error"] = False
        except AuditError:
            checks["aggregate_malformed_candidate_controlled_error"] = True
        workload_bad = root / "workload-bad.yaml"
        workload_bad.write_text(yaml.safe_dump({
            "frozen_workload_dag": {
                "repetitions": 3,
                "routes": [
                    {"id": "dup", "argv": "pytest", "environment_id": "missing", "base_mapping": "x", "head_mapping": "x", "cwd": ".", "env": {}},
                    {"id": "dup", "argv": ["pytest"], "environment_id": "missing", "base_mapping": "x", "head_mapping": "x", "cwd": ".", "env": {}},
                ],
                "edges": [{"from": "dup"}], "measurements": [],
            },
        }), encoding="utf-8")
        workload_errors, _ = validate_documents([workload_bad], dt.date.today())
        checks["workload_duplicate_argv_env_edge_rejected"] = all(
            any(fragment in error for error in workload_errors)
            for fragment in ("duplicate route", "argv must", "unknown environment", "from/to required")
        )
        ledger_bad = root / "ledger-bad.yaml"
        common_duration = {"collection": 0, "setup": 0, "call": 1, "cost_class": "fast"}
        def malicious_observation(nodeid: str, outcome: str) -> dict[str, Any]:
            return {
                "environment_id": "missing", "nodeid": nodeid,
                "collection_state": "collected", "outcome": outcome,
                "skip_reason": None, "markers": [], "duration": common_duration,
                "artifact_hash": "0" * 64,
            }
        ledger_bad.write_text(yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [{
            "candidate": {
                "id": "bad", "members": ["stale-member"], "granularity": "family",
                "source_paths": "tests/x.py", "production_paths": [], "oracle": "oracle",
                "contract_claim": "claim", "authority": ["authority"], "duplicate_group": None,
                "route_memberships": [], "platforms": {"linux": True},
                "observations": [
                    malicious_observation("n1", "passed"),
                    malicious_observation("n2", "failed"),
                ],
                "equivalence": {
                    "production_path": "x", "oracle": "x", "outcome": "same",
                    "route_role": "owner", "cost_class": "fast",
                    "platform": "linux", "disposition": "KEEP",
                },
            },
            "evidence": {"profile": "inert", "routing_evidence": ["x"], "authority_evidence": ["x"]},
            "verdict": "KEEP", "state": "terminal", "action": "keep",
            "review": {"implementer": "a", "independent_reviewer": "b", "verdict": "approved", "timestamp": "2026-08-10T00:00:00Z"},
        }]}), encoding="utf-8")
        ledger_errors, _ = validate_documents([ledger_bad], dt.date.today())
        checks["ledger_types_refs_keep_family_rejected"] = all(
            any(fragment in error for error in ledger_errors)
            for fragment in ("source_paths must", "platforms must", "stale/unknown", "causal_probe", "divergent family")
        )

        valid_environment_body: dict[str, Any] = {
            "os": "selftest-os", "runner_image": "selftest-runner", "cpu_class": "selftest-cpu",
            "python": "CPython 3.13.1", "event": "local", "env": {}, "lock_hash": "1" * 64,
            "install_command": ["uv", "sync", "--frozen"], "install_state": "clean",
            "workers": "serial", "cache_policy": "disabled", "harness_patch_hash": None,
        }
        valid_environment = {"id": _sha(_json_bytes(valid_environment_body)), **valid_environment_body}
        environment_errors: list[str] = []
        validate_environment(valid_environment, "environment", environment_errors)
        checks["valid_empty_environment"] = environment_errors == []
        environment_id = cast(str, valid_environment["id"])

        member_a = "tests/test_schema.py::test_a"
        member_b = "tests/test_schema.py::test_b"
        census_identities = {member_a, member_b}
        valid_observation: dict[str, Any] = {
            "environment_id": environment_id, "nodeid": member_a, "collection_state": "collected",
            "outcome": "passed", "skip_reason": None, "markers": [],
            "duration": {"collection": 0.0, "setup": 0.0, "call": 0.01, "cost_class": "fast"},
            "artifact_hash": "2" * 64,
        }
        valid_disposition: dict[str, Any] = {
            "candidate": {
                "id": "schema-candidate", "members": [member_a], "granularity": "function",
                "source_paths": ["tests/test_schema.py"], "production_paths": [], "oracle": None,
                "contract_claim": None, "authority": ["selftest-authority"], "duplicate_group": None,
                "route_memberships": [{
                    "route_id": "selftest", "role": "owner", "required": True, "events": [],
                    "selector": {"paths": ["tests/"], "markers": [], "ignores": [], "environment_id": environment_id},
                }],
                "platforms": ["selftest-os"], "observations": [valid_observation],
            },
            "evidence": {
                "profile": "inert", "routing_evidence": [{
                    "route_id": "selftest", "role": "owner", "required": True, "events": [],
                    "selector": {"paths": ["tests/"], "markers": [], "ignores": [], "environment_id": environment_id},
                    "result": "selected by frozen route",
                }],
                "authority_evidence": [{"reference": "selftest-authority", "result": "current authority"}],
            },
            "verdict": "DELETE", "state": "terminal", "action": "delete", "survivor": None,
            "issue": None, "owner": None, "expires": None, "hic_approval": None,
            "review": {
                "implementer": "selftest", "independent_reviewer": "reviewer", "verdict": "approved",
                "timestamp": "2026-08-10T00:00:00Z",
            },
        }

        synthetic_nodes = {member_a, member_b}
        synthetic_member_nodes = {member_a: {member_a}, member_b: {member_b}}
        synthetic_member_states = {member_a: "collected", member_b: "collected"}
        synthetic_route_authority: dict[str, Mapping[str, Any]] = {
            "selftest": {"environment_id": environment_id, "env": {}},
        }

        def disposition_errors(row: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_disposition(
                row, 0, dt.date(2026, 8, 10), found, census_identities, {environment_id},
                synthetic_nodes, synthetic_member_nodes, synthetic_member_states, synthetic_route_authority,
            )
            return found

        checks["valid_empty_markers"] = disposition_errors(copy.deepcopy(valid_disposition)) == []
        invalid_action = copy.deepcopy(valid_disposition)
        invalid_action["action"] = ["delete"]
        checks["action_type_rejected"] = any("action must" in error for error in disposition_errors(invalid_action))
        invalid_survivor = copy.deepcopy(valid_disposition)
        invalid_survivor["survivor"] = [member_a]
        checks["survivor_type_rejected"] = any("survivor must" in error for error in disposition_errors(invalid_survivor))

        evidence_bad_values: dict[str, Any] = {
            "caller_evidence": {}, "authority_evidence": {}, "routing_evidence": {},
            "overlap_evidence": {}, "base_evidence": [], "causal_probe": [], "cost_evidence": [],
        }
        for field, bad_value in evidence_bad_values.items():
            invalid_evidence = copy.deepcopy(valid_disposition)
            invalid_evidence["evidence"][field] = bad_value
            checks[f"evidence_type_{field}_rejected"] = any(
                field in error for error in disposition_errors(invalid_evidence)
            )
        scalar_evidence_member = copy.deepcopy(valid_disposition)
        scalar_evidence_member["evidence"]["authority_evidence"] = ["bare-reference"]
        checks["evidence_scalar_member_rejected"] = any(
            "list of mapping evidence rows" in error for error in disposition_errors(scalar_evidence_member)
        )
        vacuous_values: dict[str, Any] = {
            "caller_evidence": [{}], "authority_evidence": [{}], "routing_evidence": [{}],
            "overlap_evidence": [{}], "base_evidence": {}, "cost_evidence": {},
        }
        for field, vacuous_value in vacuous_values.items():
            vacuous_evidence = copy.deepcopy(valid_disposition)
            vacuous_evidence["evidence"][field] = vacuous_value
            checks[f"evidence_vacuous_{field}_rejected"] = any(
                field in error for error in disposition_errors(vacuous_evidence)
            )
        nested_bad_values: dict[str, Any] = {
            "caller_evidence": [{"command": 123, "result": {}}],
            "authority_evidence": [{"reference": 123, "result": []}],
            "routing_evidence": [{"route_id": 123, "role": [], "required": "yes", "events": {}, "selector": [], "result": 0}],
            "overlap_evidence": [{"left": 1, "right": [], "result": {}}],
            "base_evidence": {"identity": [], "result": {}},
            "cost_evidence": {"identity": 123, "result": []},
        }
        for field, bad_value in nested_bad_values.items():
            invalid_nested = copy.deepcopy(valid_disposition)
            invalid_nested["evidence"][field] = bad_value
            checks[f"evidence_nested_{field}_rejected"] = any(
                field in error for error in disposition_errors(invalid_nested)
            )
        fabricated_observation = copy.deepcopy(valid_disposition)
        fabricated_observation["candidate"]["observations"][0]["nodeid"] = "tests/not-in-census.py::test_fabricated"
        checks["fabricated_observation_node_rejected"] = any(
            "nodeid absent from census" in error for error in disposition_errors(fabricated_observation)
        )
        wrong_member_observation = copy.deepcopy(valid_disposition)
        wrong_member_observation["candidate"]["observations"][0]["nodeid"] = member_b
        checks["observation_candidate_membership_rejected"] = any(
            "does not belong to candidate members" in error for error in disposition_errors(wrong_member_observation)
        )
        null_collected_observation = copy.deepcopy(valid_disposition)
        null_collected_observation["candidate"]["observations"][0]["nodeid"] = None
        checks["null_collected_observation_rejected"] = any(
            "nodeid null only for source-only states" in error for error in disposition_errors(null_collected_observation)
        )
        unknown_candidate_route = copy.deepcopy(valid_disposition)
        unknown_candidate_route["candidate"]["route_memberships"][0]["route_id"] = "missing-route"
        checks["unknown_candidate_route_rejected"] = any(
            "unknown frozen route_id" in error for error in disposition_errors(unknown_candidate_route)
        )
        mismatched_route_environment = copy.deepcopy(valid_disposition)
        mismatched_route_environment["candidate"]["route_memberships"][0]["selector"]["environment_id"] = "missing-env"
        checks["candidate_route_environment_rejected"] = any(
            "environment_id does not match frozen route" in error
            for error in disposition_errors(mismatched_route_environment)
        )
        mismatched_evidence_role = copy.deepcopy(valid_disposition)
        mismatched_evidence_role["evidence"]["routing_evidence"][0]["role"] = "coverage"
        checks["evidence_route_role_rejected"] = any(
            "role does not match candidate" in error for error in disposition_errors(mismatched_evidence_role)
        )
        unknown_evidence_route = copy.deepcopy(valid_disposition)
        unknown_evidence_route["evidence"]["routing_evidence"][0]["route_id"] = "missing-route"
        checks["unknown_evidence_route_rejected"] = any(
            "unknown frozen route_id" in error for error in disposition_errors(unknown_evidence_route)
        )
        mismatched_evidence_environment = copy.deepcopy(valid_disposition)
        mismatched_evidence_environment["evidence"]["routing_evidence"][0]["selector"]["environment_id"] = "missing-env"
        checks["evidence_route_environment_rejected"] = any(
            "environment_id does not match frozen route" in error
            for error in disposition_errors(mismatched_evidence_environment)
        )
        source_only_observation = copy.deepcopy(valid_disposition)
        source_only_observation["candidate"]["observations"][0].update({
            "nodeid": None, "collection_state": "zero_node", "outcome": "not_run",
        })
        source_only_errors: list[str] = []
        validate_disposition(
            source_only_observation, 0, dt.date(2026, 8, 10), source_only_errors,
            census_identities, {environment_id}, synthetic_nodes,
            {member_a: set(), member_b: {member_b}},
            {member_a: "zero_node", member_b: "collected"}, synthetic_route_authority,
        )
        checks["valid_source_only_null_observation"] = source_only_errors == []

        valid_temporary = copy.deepcopy(valid_disposition)
        valid_temporary.update({
            "verdict": "TEMPORARY", "action": "temporary exception", "issue": "ISSUE-1", "owner": "owner",
            "expires": "2026-08-20", "hic_approval": "one-time approval", "renewal": False,
        })
        valid_temporary["evidence"] = {
            "profile": "environmental_platform",
            "base_evidence": {"identity": "environmental failure", "result": "reproduced"},
            "routing_evidence": copy.deepcopy(valid_disposition["evidence"]["routing_evidence"]),
        }
        checks["valid_temporary"] = disposition_errors(valid_temporary) == []
        for field, bad_value in {
            "hic_approval": ["approval"], "issue": {"id": "ISSUE-1"}, "owner": ["owner"],
            "expires": ["2026-08-20"], "renewal": "false",
        }.items():
            invalid_temporary = copy.deepcopy(valid_temporary)
            invalid_temporary[field] = bad_value
            checks[f"temporary_{field}_type_rejected"] = any(
                field in error for error in disposition_errors(invalid_temporary)
            )

        family = copy.deepcopy(valid_disposition)
        family["candidate"].update({
            "members": [member_a, member_b], "granularity": "family",
            "observations": [
                valid_observation,
                {**valid_observation, "nodeid": member_b, "outcome": "failed"},
            ],
            "equivalence": {
                "production_path": "src/schema.py", "oracle": "result", "outcome": "mixed",
                "route_role": "owner", "cost_class": "fast", "platform": "selftest-os",
                "disposition": "DELETE",
            },
            "divergent_dimensions": ["outcome"],
        })
        node_row_base = {
            "production_path": "src/schema.py", "oracle": "result", "route_role": "owner",
            "cost_class": "fast", "platform": "selftest-os", "disposition": "DELETE",
        }
        family["candidate"]["node_rows"] = [
            {"member": member_a, **node_row_base, "outcome": "passed"},
            {"member": member_b, **node_row_base, "outcome": "failed"},
        ]
        checks["valid_divergent_family_expansion"] = disposition_errors(family) == []
        invalid_dimension = copy.deepcopy(family)
        invalid_dimension["candidate"]["equivalence"]["oracle"] = ["result"]
        checks["equivalence_dimension_type_rejected"] = any(
            "equivalence.oracle" in error for error in disposition_errors(invalid_dimension)
        )
        empty_rows = copy.deepcopy(family)
        empty_rows["candidate"]["node_rows"] = []
        checks["divergent_empty_node_rows_rejected"] = any(
            "nonempty node_rows" in error for error in disposition_errors(empty_rows)
        )
        empty_row = copy.deepcopy(family)
        empty_row["candidate"]["node_rows"] = [{}]
        checks["divergent_empty_node_row_rejected"] = any(
            "member must" in error for error in disposition_errors(empty_row)
        )
        missing_member_row = copy.deepcopy(family)
        missing_member_row["candidate"]["node_rows"] = missing_member_row["candidate"]["node_rows"][:1]
        checks["divergent_member_coverage_rejected"] = any(
            "cover every candidate member" in error for error in disposition_errors(missing_member_row)
        )
        missing_dimension_row = copy.deepcopy(family)
        del missing_dimension_row["candidate"]["node_rows"][0]["platform"]
        checks["divergent_dimension_coverage_rejected"] = any(
            "missing field platform" in error for error in disposition_errors(missing_dimension_row)
        )
        unknown_member_row = copy.deepcopy(family)
        unknown_member_row["candidate"]["node_rows"][0]["member"] = "tests/test_schema.py::test_unknown"
        checks["divergent_unknown_identity_rejected"] = any(
            "candidate and census identity" in error for error in disposition_errors(unknown_member_row)
        )
        nonvarying_rows = copy.deepcopy(family)
        nonvarying_rows["candidate"]["node_rows"][1]["outcome"] = "passed"
        checks["divergent_dimension_must_vary"] = any(
            "must vary" in error for error in disposition_errors(nonvarying_rows)
        )

        duplicate_environments = root / "duplicate-environments.yaml"
        duplicate_environments.write_text(yaml.safe_dump({"environments": [valid_environment, valid_environment]}), encoding="utf-8")
        duplicate_environment_errors, _ = validate_documents([duplicate_environments], dt.date.today())
        checks["duplicate_environment_id_rejected"] = any(
            "duplicate environment id" in error for error in duplicate_environment_errors
        )
        duplicate_candidates = root / "duplicate-candidates.yaml"
        duplicate_candidates.write_text(yaml.safe_dump({
            "schema_version": SCHEMA, "environments": [valid_environment],
            "dispositions": [valid_disposition, valid_disposition],
        }), encoding="utf-8")
        duplicate_candidate_errors, _ = validate_documents([duplicate_candidates], dt.date.today())
        checks["duplicate_candidate_id_rejected"] = any(
            "duplicate candidate id" in error for error in duplicate_candidate_errors
        )

        report_root = Path(__file__).resolve().parent
        committed_census_path = report_root / "raw" / "base-census.json"
        committed_workload_path = report_root / "raw" / "base-workloads.yaml"
        committed_census = cast(dict[str, Any], json.loads(committed_census_path.read_text(encoding="utf-8")))
        committed_workload = cast(dict[str, Any], yaml.safe_load(committed_workload_path.read_text(encoding="utf-8")))
        inert_manifest = committed_census["manifests"]["inert_candidates"][0]
        committed_member = cast(str, inert_manifest["member"])
        source_row = next(row for row in committed_census["source_units"] if row["id"] == committed_member)
        committed_node_ref = cast(list[int], source_row["node_refs"])[0]
        compact_node = cast(list[Any], committed_census["collection"]["nodes"][committed_node_ref])
        committed_nodeid = cast(str, compact_node[0])
        marker_ref = cast(int, compact_node[4])
        reason_ref = compact_node[6]
        committed_markers = cast(list[str], committed_census["collection"]["tables"]["marker_sets"][marker_ref])
        committed_reason = (
            cast(str, committed_census["collection"]["tables"]["reasons"][reason_ref])
            if isinstance(reason_ref, int) else "; ".join(cast(list[str], inert_manifest["reasons"]))
        )
        full_collection_route = next(
            route for route in committed_workload["frozen_workload_dag"]["routes"]
            if route["id"] == "full-collection"
        )
        committed_environment_id = cast(str, full_collection_route["environment_id"])
        committed_selector = {
            "paths": ["tests/"], "markers": [], "ignores": ["tests/sync/test_orphan_sweep.py"],
            "environment_id": committed_environment_id,
        }
        committed_membership = {
            "route_id": "full-collection", "role": "owner", "required": True,
            "events": ["local"], "selector": committed_selector,
        }
        committed_positive: dict[str, Any] = {
            "candidate": {
                "id": "selftest-committed-inert-delete", "members": [committed_member], "granularity": "function",
                "source_paths": [cast(str, source_row["path"])], "production_paths": [], "oracle": None,
                "contract_claim": None, "authority": ["WP03 inert-state adjudication"], "duplicate_group": None,
                "route_memberships": [committed_membership], "platforms": ["macOS"],
                "observations": [{
                    "environment_id": committed_environment_id, "nodeid": committed_nodeid,
                    "collection_state": "collected", "outcome": "skipped", "skip_reason": committed_reason,
                    "markers": committed_markers,
                    "duration": {"collection": 0.0, "setup": 0.0, "call": 0.0, "cost_class": "not_run"},
                    "artifact_hash": _sha(committed_census_path.read_bytes()),
                }],
            },
            "evidence": {
                "profile": "inert",
                "routing_evidence": [{**committed_membership, "result": "present in frozen full collection route"}],
                "authority_evidence": [{
                    "reference": "kitty-specs/assertive-test-suite-sanitation-01KZME3P/tasks/WP03-inert-test-states.md",
                    "result": "assigned inert-state authority for adjudication",
                }],
            },
            "verdict": "DELETE", "state": "terminal", "action": "delete after inert adjudication",
            "survivor": None, "issue": None, "owner": None, "expires": None, "hic_approval": None,
            "review": {
                "implementer": "selftest", "independent_reviewer": "selftest-reviewer", "verdict": "approved",
                "timestamp": "2026-08-10T00:00:00Z",
            },
        }
        committed_positive_shard = root / "committed-positive-delete.yaml"
        committed_positive_shard.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [committed_positive]}), encoding="utf-8",
        )
        committed_positive_errors, _ = validate_documents(
            [committed_census_path, committed_workload_path, committed_positive_shard], dt.date(2026, 8, 10),
        )
        checks["committed_positive_delete_valid"] = committed_positive_errors == []

        combined_bypass = copy.deepcopy(committed_positive)
        combined_bypass["candidate"]["observations"][0]["nodeid"] = "tests/not-in-census.py::test_fabricated"
        combined_bypass["candidate"]["route_memberships"][0]["route_id"] = "does-not-exist"
        combined_bypass["evidence"]["authority_evidence"] = [{}]
        combined_bypass["evidence"]["routing_evidence"] = [{}]
        combined_bypass_shard = root / "committed-combined-bypass.yaml"
        combined_bypass_shard.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [combined_bypass]}), encoding="utf-8",
        )
        combined_errors, _ = validate_documents(
            [committed_census_path, committed_workload_path, combined_bypass_shard], dt.date(2026, 8, 10),
        )
        checks["combined_relational_bypass_rejected"] = all(
            any(fragment in error for error in combined_errors)
            for fragment in (
                "nodeid absent from census", "nodeid does not belong", "unknown frozen route_id",
                "authority_evidence[0]", "routing_evidence[0]",
            )
        )

        valid_route = {
            "id": "route", "argv": ["pytest"], "environment_id": environment_id,
            "base_mapping": "tests/", "head_mapping": "tests/", "cwd": ".", "env": {},
        }
        valid_measurement = {
            "route_id": "route", "environment_id": environment_id, "collection": 1.0, "setup": 2.0,
            "call": 3.0, "wall": 4.0, "compute": 6.0, "outcome": "passed", "artifact_hash": "3" * 64,
        }

        def find_workload_errors(dag: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_workload(dag, "workload", found, {environment_id})
            return found

        valid_workload: dict[str, Any] = {
            "routes": [valid_route], "edges": [], "repetitions": 3, "measurements": [valid_measurement],
        }
        checks["valid_typed_measurement"] = find_workload_errors(valid_workload) == []
        duplicate_edges = copy.deepcopy(valid_workload)
        duplicate_edges["edges"] = [{"from": "route", "to": "route"}, {"from": "route", "to": "route"}]
        checks["duplicate_dag_edge_rejected"] = any("duplicate dependency edge" in error for error in find_workload_errors(duplicate_edges))
        for field in ("collection", "setup", "call", "wall", "compute"):
            invalid_measurement = copy.deepcopy(valid_workload)
            invalid_measurement["measurements"][0][field] = "1"
            checks[f"measurement_{field}_rejected"] = any(
                "timing fields" in error for error in find_workload_errors(invalid_measurement)
            )
        for field, bad_value, fragment in (
            ("outcome", ["passed"], "invalid outcome"),
            ("artifact_hash", {"sha": "3" * 64}, "artifact_hash must"),
            ("environment_id", "missing", "unknown environment_id"),
            ("route_id", "missing", "unknown route_id"),
        ):
            invalid_measurement = copy.deepcopy(valid_workload)
            invalid_measurement["measurements"][0][field] = bad_value
            checks[f"measurement_{field}_rejected"] = any(
                fragment in error for error in find_workload_errors(invalid_measurement)
            )
        if not all(checks.values()):
            raise AuditError("selftest failures: " + ", ".join(key for key, value in checks.items() if not value))
        return {"valid": True, "checks": checks}


def _write(path: Path | None, value: Any, yaml_output: bool = False) -> None:
    text = yaml.safe_dump(_stable(value), sort_keys=True, allow_unicode=True) if yaml_output else _json_bytes(value).decode()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snap = commands.add_parser("snapshot")
    snap.add_argument("--root", type=Path, default=Path.cwd())
    snap.add_argument("--tests", "--tests-path", dest="tests_path", default="tests")
    snap.add_argument("--inventory-sha")
    snap.add_argument("--output", type=Path)
    snap.add_argument("pytest_args", nargs=argparse.REMAINDER)
    val = commands.add_parser("validate")
    val.add_argument("paths", nargs="+", type=Path)
    val.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    val.add_argument("--output", type=Path)
    agg = commands.add_parser("aggregate")
    agg.add_argument("paths", nargs="+", type=Path)
    agg.add_argument("--output", type=Path)
    commands.add_parser("selftest")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(args.root, args.tests_path, args.pytest_args, args.inventory_sha)
            reconciliation = result["reconciliation"]
            ownership = result["ownership"]
            if not reconciliation["complete"] or not ownership["complete"]:
                raise AuditError(
                    "snapshot incomplete: "
                    f"unreconciled_nodes={len(reconciliation['unreconciled_or_duplicate_nodes'])}; "
                    f"unowned_candidates={len(ownership['unowned'])}; "
                    f"unreconciled_sample={reconciliation['unreconciled_or_duplicate_nodes'][:5]}; "
                    f"unowned_sample={ownership['unowned'][:5]}"
                )
            _write(args.output, result)
        elif args.command == "validate":
            errors, summary = validate_documents(args.paths, args.today)
            result = {"valid": not errors, "errors": errors, **summary}
            _write(args.output, result)
            return 0 if not errors else 1
        elif args.command == "aggregate":
            result = aggregate(args.paths)
            errors, _ = validate_documents(args.paths, dt.date.today())
            if errors:
                raise AuditError("aggregate inputs invalid: " + "; ".join(errors))
            _write(args.output, result, yaml_output=True)
        else:
            _write(None, selftest())
    except AuditError as exc:
        print(f"audit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
