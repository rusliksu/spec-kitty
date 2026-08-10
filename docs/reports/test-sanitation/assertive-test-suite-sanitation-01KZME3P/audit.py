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
import dataclasses
import datetime as dt
import fnmatch
import hashlib
import importlib.metadata
import io
import json
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
GRANULARITIES = {"function", "family", "duplicate_cluster", "node"}
ROUTE_ROLES = {"owner", "coverage", "platform", "hard_gate"}
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


def discover_source(root: Path, tests_root: Path) -> tuple[list[SourceUnit], list[dict[str, str]]]:
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
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and TEST_NAME.match(node.name):
                units.append(_unit(rel, node.name, node, sorted(module_markers)))
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                inherited = sorted(module_markers | {_decorator_name(item) for item in node.decorator_list})
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and TEST_NAME.match(child.name):
                        units.append(_unit(rel, f"{node.name}.{child.name}", child, inherited))
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
        self.errors: list[dict[str, str]] = []
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

    def pytest_collection_modifyitems(self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
        del session, config
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
                "path": Path(path).as_posix(), "line": line + 1,
                "parent_source_function": source_name.split("[")[0],
                # Arguments (especially parametrize payloads) are not inventory
                # identity and can be enormous; effective marker names plus the
                # dedicated skip/xfail reason retain every required distinction.
                "markers": sorted(marker_names),
                "quarantined": "quarantine" in marker_names,
                "skip_or_xfail_reason": reason,
            })

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        self.deselected.extend(item.nodeid.replace("\\", "/") for item in items)

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.errors.append({"nodeid": report.nodeid.replace("\\", "/"), "error": _stable(str(report.longrepr))})


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
        "collection_errors": sorted(plugin.errors, key=lambda row: row["nodeid"]),
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
        "deselected": collection["deselected"], "collection_errors": collection["collection_errors"],
        "ignored_paths": collection["ignored_paths"],
    }


def _reconcile(units: Sequence[SourceUnit], collection: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes = collection["nodes"]
    errors = collection["collection_errors"]
    deselected = set(collection["deselected"])
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
        matched_deselected = [nodeid for nodeid in deselected if nodeid.startswith(f"{unit.path}::") and unit.qualname.split(".")[-1] in nodeid]
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
        "complete": not bad_nodes and len(rows) == len(units),
    }


def snapshot(root: Path, tests_path: str, extra_args: Sequence[str], inventory_sha: str | None) -> dict[str, Any]:
    root = root.resolve()
    tests_root = (root / tests_path).resolve()
    units, parse_errors = discover_source(root, tests_root)
    config = discover_config(root)
    collection = collect_pytest(root, tests_root, extra_args) if tests_root.exists() else {
        "argv": ["pytest", tests_path, "--collect-only", "-q", "-p", "no:cacheprovider"],
        "exit_code": 5, "nodes": [], "deselected": [], "collection_errors": [], "ignored_paths": [],
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
        "source_units": compact_rows, "collection": _compact_collection(collection),
        "reconciliation": reconciliation, "manifests": manifests,
        "ownership": {"unowned": sorted(set(unowned)), "complete": not unowned},
        "empty_tests_root": not units and not collection["nodes"],
    }
    evidence["content_sha256"] = _sha(_json_bytes(evidence))
    return cast(dict[str, Any], _stable(evidence))


def _required(row: Mapping[str, Any], fields: Iterable[str], where: str, errors: list[str]) -> None:
    for field in fields:
        if row.get(field) in (None, "", [], {}):
            errors.append(f"{where}: missing {field}")


def _keys(row: Mapping[str, Any], fields: Iterable[str], where: str, errors: list[str]) -> None:
    for field in fields:
        if field not in row:
            errors.append(f"{where}: missing field {field}")


def validate_environment(env: Mapping[str, Any], where: str, errors: list[str]) -> None:
    required = (
        "id", "os", "runner_image", "cpu_class", "python", "event", "env", "lock_hash",
        "install_command", "install_state", "workers", "cache_policy", "harness_patch_hash",
    )
    _keys(env, required, where, errors)
    _required(env, required[:-1], where, errors)
    if not isinstance(env.get("env"), dict) or not isinstance(env.get("install_command"), list):
        errors.append(f"{where}: env must be mapping and install_command must be list")
    if env.get("event") not in {"local", "PR", "push", "schedule", "manual"}:
        errors.append(f"{where}: invalid event")
    body = {key: env.get(key) for key in required if key != "id"}
    if env.get("id") != _sha(_json_bytes(body)):
        errors.append(f"{where}: id is not SHA-256 of normalized environment fields")


def validate_route(route: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(route, ("route_id", "role", "required", "events", "selector"), where, errors)
    _required(route, ("route_id", "role", "events", "selector"), where, errors)
    if route.get("role") not in ROUTE_ROLES:
        errors.append(f"{where}: invalid route role")
    if not isinstance(route.get("required"), bool):
        errors.append(f"{where}: required must be boolean")
    if not isinstance(route.get("events"), list) or not isinstance(route.get("selector"), dict):
        errors.append(f"{where}: events must be list and selector must be mapping")


def validate_causal_probe(probe: Any, where: str, errors: list[str]) -> None:
    if not isinstance(probe, dict):
        errors.append(f"{where}: causal_probe must be mapping")
        return
    fields = (
        "kind", "fault", "authority_violated", "act_reached", "intended_oracle",
        "intended_oracle_failed", "command", "environment", "raw_artifact_hash",
    )
    _required(probe, fields, where, errors)
    if probe.get("act_reached") is not True or probe.get("intended_oracle_failed") is not True:
        errors.append(f"{where}: causal proof must reach Act and fail intended oracle")


def validate_workload(dag: Mapping[str, Any], where: str, errors: list[str]) -> None:  # noqa: C901 - schema branches are intentionally explicit
    _keys(dag, ("routes", "edges", "repetitions", "measurements"), where, errors)
    routes = dag.get("routes", [])
    edges = dag.get("edges", [])
    if not isinstance(routes, list) or not isinstance(edges, list) or not isinstance(dag.get("measurements"), list):
        errors.append(f"{where}: routes, edges, and measurements must be lists")
        return
    if not isinstance(dag.get("repetitions"), int) or dag.get("repetitions", 0) < 3:
        errors.append(f"{where}: repetitions must be >= 3")
    route_ids = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"{where}.routes[{index}]: mapping required")
            continue
        _required(route, ("id", "argv", "environment_id", "base_mapping", "head_mapping"), f"{where}.routes[{index}]", errors)
        route_ids.add(route.get("id"))
    graph: dict[Any, set[Any]] = {route_id: set() for route_id in route_ids}
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict) or set(edge) < {"from", "to"}:
            errors.append(f"{where}.edges[{index}]: from/to required")
            continue
        if edge["from"] not in route_ids or edge["to"] not in route_ids:
            errors.append(f"{where}.edges[{index}]: unknown route")
        graph.setdefault(edge["from"], set()).add(edge["to"])
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
        _required(measurement, ("route_id", "collection", "setup", "call", "wall", "compute", "outcome", "artifact_hash"), f"{where}.measurements[{index}]", errors)
        if measurement.get("route_id") not in route_ids:
            errors.append(f"{where}.measurements[{index}]: unknown route")


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
    states = {row.get("collection_state") for row in units if isinstance(row, dict)}
    if not states <= COLLECTION_STATES:
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
    _required(row, ("hic_approval", "issue", "owner", "expires"), where, errors)
    if profile != "environmental_platform":
        errors.append(f"{where}: TEMPORARY only permits environmental_platform")
    if row.get("renewal"):
        errors.append(f"{where}: TEMPORARY cannot renew")
    try:
        expiry = dt.date.fromisoformat(str(row.get("expires")))
        if expiry < today or expiry > today + dt.timedelta(days=30):
            errors.append(f"{where}: TEMPORARY expiry must be today..today+30d")
    except ValueError:
        errors.append(f"{where}: invalid TEMPORARY expiry")


def validate_disposition(row: Mapping[str, Any], index: int, today: dt.date, errors: list[str]) -> None:  # noqa: C901 - fail-closed schema matrix
    where = f"dispositions[{index}]"
    _required(row, ("candidate", "evidence", "verdict", "state", "action", "review"), where, errors)
    verdict, state = row.get("verdict"), row.get("state")
    if verdict not in VERDICTS:
        errors.append(f"{where}: unknown verdict {verdict!r}")
    if state == "terminal" and verdict in {"FIX_TEST", "FIX_PRODUCT"}:
        errors.append(f"{where}: FIX_* cannot be terminal")
    if state not in {"pending", "terminal"}:
        errors.append(f"{where}: state must be pending or terminal")
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
    _required(candidate, ("id", "members", "granularity", "source_paths", "route_memberships", "platforms", "observations"), f"{where}.candidate", errors)
    if candidate.get("granularity") not in GRANULARITIES:
        errors.append(f"{where}: invalid granularity")
    profile = evidence.get("profile")
    if profile not in PROFILES:
        errors.append(f"{where}: invalid evidence profile {profile!r}")
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
    if profile in requirements:
        _required(evidence, requirements[profile], f"{where}.evidence[{profile}]", errors)
    if isinstance(profile, str) and "causal_probe" in requirements.get(profile, ()):
        validate_causal_probe(evidence.get("causal_probe"), f"{where}.evidence.causal_probe", errors)
    observations = candidate.get("observations", [])
    if not isinstance(observations, list):
        errors.append(f"{where}.observations: list required")
        observations = []
    for obs_index, obs in enumerate(observations):
        if not isinstance(obs, dict):
            errors.append(f"{where}.observations[{obs_index}]: mapping required")
            continue
        if obs.get("collection_state") not in COLLECTION_STATES or obs.get("outcome") not in OUTCOMES:
            errors.append(f"{where}.observations[{obs_index}]: invalid state/outcome")
        observation_fields = (
            "environment_id", "nodeid", "collection_state", "outcome", "skip_reason",
            "markers", "duration", "artifact_hash",
        )
        _keys(obs, observation_fields, f"{where}.observations[{obs_index}]", errors)
        _required(obs, ("environment_id", "collection_state", "markers", "duration", "artifact_hash"), f"{where}.observations[{obs_index}]", errors)
        duration = obs.get("duration")
        if not isinstance(duration, dict) or not {"collection", "setup", "call", "cost_class"} <= set(duration):
            errors.append(f"{where}.observations[{obs_index}]: typed duration fields required")
        if obs.get("outcome") in {"skipped", "xfailed"} and not obs.get("skip_reason"):
            errors.append(f"{where}.observations[{obs_index}]: skip_reason required")
    memberships = candidate.get("route_memberships", [])
    if not isinstance(memberships, list):
        errors.append(f"{where}.route_memberships: list required")
        memberships = []
    for route_index, route in enumerate(memberships):
        if isinstance(route, dict):
            validate_route(route, f"{where}.routes[{route_index}]", errors)
        else:
            errors.append(f"{where}.routes[{route_index}]: mapping required")
    if sum(isinstance(item, dict) and item.get("role") == "owner" for item in memberships) != 1:
        errors.append(f"{where}: exactly one owner route required")
    if verdict == "KEEP":
        _required(candidate, ("production_paths", "oracle", "contract_claim", "authority"), f"{where}.KEEP", errors)
    if verdict == "CONSOLIDATE" and state == "terminal":
        _required(row, ("survivor",), where, errors)
        members = candidate.get("members", [])
        if not isinstance(members, list) or len(members) < 2:
            errors.append(f"{where}: terminal consolidation needs deleted and surviving members")
    if verdict == "TEMPORARY":
        _validate_temporary(row, where, profile, today, errors)
    review = row.get("review", {})
    if isinstance(review, dict):
        _required(review, ("implementer", "independent_reviewer", "verdict", "timestamp"), f"{where}.review", errors)
    else:
        errors.append(f"{where}.review: mapping required")
    if candidate.get("granularity") in {"family", "duplicate_cluster"}:
        dimensions = candidate.get("equivalence")
        required_dimensions = {"production_path", "oracle", "outcome", "route_role", "cost_class", "platform", "disposition"}
        if not isinstance(dimensions, dict) or not required_dimensions <= set(dimensions):
            errors.append(f"{where}: family equivalence dimensions required")
        if candidate.get("divergent_dimensions") and not candidate.get("node_rows"):
            errors.append(f"{where}: divergent family dimensions require node_rows")


def validate_documents(paths: Sequence[Path], today: dt.date) -> tuple[list[str], dict[str, Any]]:  # noqa: C901 - heterogeneous document fail-closed dispatch
    errors: list[str] = []
    members: dict[str, str] = {}
    loaded = []
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
        if "source_units" in data and "reconciliation" in data:
            validate_census(data, errors)
        environments = data.get("run_environments", data.get("environments", []))
        if isinstance(environments, dict):
            environments = list(environments.values())
        for env_index, env in enumerate(environments or []):
            if isinstance(env, dict):
                validate_environment(env, f"{path}.environments[{env_index}]", errors)
            else:
                errors.append(f"{path}.environments[{env_index}]: mapping required")
        workload = data.get("frozen_workload_dag")
        if workload is not None:
            if isinstance(workload, dict):
                validate_workload(workload, f"{path}.frozen_workload_dag", errors)
            else:
                errors.append(f"{path}.frozen_workload_dag: mapping required")
        rows = data.get("dispositions", [])
        if rows and data.get("schema_version") != SCHEMA:
            errors.append(f"{path}: schema_version must be {SCHEMA}")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{path}: dispositions[{index}] must be mapping")
                continue
            validate_disposition(row, index, today, errors)
            disposition_count += 1
            candidate = row.get("candidate", {})
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
    rows = []
    source_files = []
    for path in sorted(paths):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise AuditError(f"{path}: top-level mapping required")
        source_files.append({"path": path.as_posix(), "sha256": _sha(path.read_bytes())})
        rows.extend(data.get("dispositions", []))
    rows.sort(key=lambda row: str(row.get("candidate", {}).get("id", "")))
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
            "class TestOne:\n"
            "    def test_same(self): assert True\n"
            "class TestTwo:\n"
            "    @pytest.mark.parametrize('value', [1, 2])\n"
            "    def test_same(self, value): assert value\n"
            "def test_duplicate_a(): assert 1 == 1\n"
            "def test_duplicate_b(): assert 1 == 1\n",
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
        }
        empty = root / "empty"
        (empty / "tests").mkdir(parents=True)
        empty_snapshot = snapshot(empty, "tests", [], "SELFTEST-EMPTY")
        checks["explicit_empty_census"] = (
            empty_snapshot["empty_tests_root"] is True
            and empty_snapshot["reconciliation"]["source_units"] == 0
            and empty_snapshot["collection"]["exit_code"] == 5
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
        checks["divergent_family_fails"] = any("divergent family dimensions require node_rows" in error for error in duplicate_errors)
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
