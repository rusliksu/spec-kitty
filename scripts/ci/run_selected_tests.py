"""Run an exact, data-supplied pytest inventory for manual CI evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

import pytest


PATHS_ENV = "SPEC_KITTY_TEST_PATHS_JSON"
COUNT_ENV = "SPEC_KITTY_EXPECTED_TEST_COUNT"


def load_test_paths(raw: str, *, repo_root: Path) -> list[str]:
    """Validate existing ``tests/*.py`` paths or node IDs from a JSON array."""
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{PATHS_ENV} must be valid JSON: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{PATHS_ENV} must be a non-empty JSON array")

    tests_root = (repo_root / "tests").resolve()
    paths: list[str] = []
    for value in payload:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{PATHS_ENV} entries must be non-empty strings")
        if any(character in value for character in ("\0", "\r", "\n")):
            raise ValueError(f"unsafe test selector: {value!r}")
        file_value, separator, node_suffix = value.partition("::")
        if separator and not node_suffix:
            raise ValueError(f"test node selector has no node ID: {value!r}")
        posix_path = PurePosixPath(file_value)
        if (
            posix_path.is_absolute()
            or not posix_path.parts
            or posix_path.parts[0] != "tests"
            or ".." in posix_path.parts
            or posix_path.suffix != ".py"
        ):
            raise ValueError(f"unsafe test selector: {value!r}")
        resolved = (repo_root / Path(*posix_path.parts)).resolve()
        if not resolved.is_relative_to(tests_root) or not resolved.is_file():
            raise ValueError(f"test path does not resolve to a file under tests/: {value!r}")
        paths.append(value)

    if len(paths) != len(set(paths)):
        raise ValueError(f"{PATHS_ENV} must not contain duplicate paths")
    return paths


class _ExactCollection:
    def __init__(self, expected: int) -> None:
        self.expected = expected

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        actual = len(session.items)
        if actual != self.expected:
            raise pytest.UsageError(
                f"exact inventory mismatch: expected {self.expected} tests, collected {actual}"
            )
        print(f"exact inventory confirmed: {actual} tests")


def main() -> int:
    repo_root = Path.cwd().resolve()
    try:
        expected = int(os.environ[COUNT_ENV])
        if expected <= 0:
            raise ValueError(f"{COUNT_ENV} must be a positive integer")
        paths = load_test_paths(os.environ[PATHS_ENV], repo_root=repo_root)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}")
        return int(pytest.ExitCode.USAGE_ERROR)

    report = repo_root / "out" / "reports" / "wp03-windows-exact.xml"
    report.parent.mkdir(parents=True, exist_ok=True)
    return pytest.main(
        [*paths, "-q", "--tb=short", f"--junitxml={report}"],
        plugins=[_ExactCollection(expected)],
    )


if __name__ == "__main__":
    raise SystemExit(main())
