"""Executable contract for the manual exact-inventory CI helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ci.run_selected_tests import COUNT_ENV, PATHS_ENV, load_test_paths


pytestmark = pytest.mark.architectural

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "run_selected_tests.py"


def test_load_test_paths_accepts_only_existing_test_files(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    assert load_test_paths(
        json.dumps(["tests/test_sample.py", "tests/test_sample.py::test_ok"]),
        repo_root=tmp_path,
    ) == ["tests/test_sample.py", "tests/test_sample.py::test_ok"]


@pytest.mark.parametrize(
    "payload",
    [
        ["../test_escape.py"],
        ["tests/../test_escape.py"],
        ["src/test_not_a_test.py"],
        ["tests/test_missing.py"],
        ["tests/test_duplicate.py::"],
        ["tests/test_duplicate.py", "tests/test_duplicate.py"],
    ],
)
def test_load_test_paths_rejects_unsafe_or_ambiguous_input(
    tmp_path: Path, payload: list[str]
) -> None:
    duplicate = tmp_path / "tests" / "test_duplicate.py"
    duplicate.parent.mkdir()
    duplicate.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_test_paths(json.dumps(payload), repo_root=tmp_path)


def test_runner_fails_closed_when_collected_count_differs(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def test_one():\n    assert True\n\n"
        "def test_two():\n    assert True\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env[PATHS_ENV] = json.dumps(["tests/test_sample.py"])
    env[COUNT_ENV] = "1"

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == int(pytest.ExitCode.USAGE_ERROR)
    assert "exact inventory mismatch: expected 1 tests, collected 2" in (
        result.stdout + result.stderr
    )
