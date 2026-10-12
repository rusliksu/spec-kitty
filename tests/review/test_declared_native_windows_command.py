"""The review port can execute a native Windows template without a shell."""

from pathlib import Path
import subprocess
import sys

import pytest

from specify_cli.review.scope_source import DeclaredCommandScopeSource

pytestmark = [pytest.mark.integration, pytest.mark.windows_ci]


def test_declared_windows_template_preserves_literal_output_argument(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)
    script = project / "report.py"
    script.write_text("import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('real report', encoding='utf-8')\n", encoding="utf-8")
    template = f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}" "{{output_file}}"'
    (project / ".kittify" / "config.yaml").write_text(f"review:\n  test_command: {template!r}\n", encoding="utf-8")
    source = DeclaredCommandScopeSource(repo_root=project)
    output = tmp_path / "literal spaces & argument.xml"
    object.__setattr__(source, "_output_file", output)
    monkeypatch.setattr(sys, "platform", "win32")

    command = source.test_command()

    assert command is not None
    assert command[0] == Path(sys.executable).as_posix()
    assert command[-1] == str(output)
    result = subprocess.run(command, cwd=project, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == "real report"
    assert not (project / "argument.xml").exists()
