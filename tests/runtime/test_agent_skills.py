"""Tests for the global managed agent-skill bootstrap."""

from __future__ import annotations

from pathlib import Path

from specify_cli.runtime.agent_skills import ensure_global_agent_skills
from specify_cli.skills.registry import SkillRegistry
from specify_cli.skills.retired import (
    RETIRED_LEGACY_SKILL_REPLACEMENTS,
    RETIRED_STANDALONE_SKILL_NAMES,
)


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _create_skill(root: Path, name: str, content: str | None = None) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        content or f"---\nname: {name}\ndescription: test\n---\n# {name}\n",
        encoding="utf-8",
    )


def test_global_bootstrap_preserves_non_spec_kitty_user_skills(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spec-kitty-test-skill")
    registry = SkillRegistry(skills_root)

    custom_skill = home / ".claude" / "skills" / "custom-skill" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True, exist_ok=True)
    custom_skill.write_text("# custom\n", encoding="utf-8")
    prefixed_custom_skill = (
        home
        / ".claude"
        / "skills"
        / "spec-kitty-user-authored"
        / "SKILL.md"
    )
    prefixed_custom_skill.parent.mkdir(parents=True)
    prefixed_custom_skill.write_text("# prefixed custom\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    managed_skill = home / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    assert managed_skill.is_file()
    assert custom_skill.is_file()
    assert custom_skill.read_text(encoding="utf-8") == "# custom\n"
    assert prefixed_custom_skill.read_text(encoding="utf-8") == "# prefixed custom\n"

    mode = managed_skill.stat().st_mode
    assert mode & 0o200 == 0


def test_global_bootstrap_removes_retired_paula_and_debbie_skills(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spec-kitty-test-skill")
    registry = SkillRegistry(skills_root)

    for root in [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]:
        for retired_name in ["debugger-debbie", "paula-patterns"]:
            retired_skill = root / retired_name / "SKILL.md"
            retired_skill.parent.mkdir(parents=True, exist_ok=True)
            retired_skill.write_text("# retired\n", encoding="utf-8")
        custom_skill = root / "custom-skill" / "SKILL.md"
        custom_skill.parent.mkdir(parents=True, exist_ok=True)
        custom_skill.write_text("# custom\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    for root in [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]:
        assert not (root / "debugger-debbie").exists()
        assert not (root / "paula-patterns").exists()
        assert (root / "custom-skill" / "SKILL.md").is_file()


def test_global_bootstrap_removes_retired_standalone_skill_surface(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spk-start-here")
    registry = SkillRegistry(skills_root)

    retired_name = next(iter(RETIRED_STANDALONE_SKILL_NAMES))
    for root in [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]:
        stale = root / retired_name / "SKILL.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("# stale standalone surface\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    for root in [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]:
        assert not (root / retired_name).exists()
    assert (home / ".agents" / "skills" / "spk-start-here" / "SKILL.md").is_file()


def test_global_bootstrap_prunes_retired_skill_even_when_version_lock_is_current(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    kittify_home = home / ".kittify"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(kittify_home))
    monkeypatch.setattr("specify_cli.runtime.agent_skills._get_cli_version", lambda: "3.2.0rc45")

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spk-start-here")
    registry = SkillRegistry(skills_root)

    retired_name = next(iter(RETIRED_STANDALONE_SKILL_NAMES))
    stale = home / ".agents" / "skills" / retired_name / "SKILL.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("# stale standalone surface\n", encoding="utf-8")

    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "agent-skills.lock").write_text("3.2.0rc45", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    assert not stale.parent.exists()
    assert (home / ".agents" / "skills" / "spk-start-here" / "SKILL.md").is_file()


def test_global_bootstrap_retires_legacy_alias_pack_even_when_version_lock_is_current(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    kittify_home = home / ".kittify"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(kittify_home))
    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._get_cli_version",
        lambda: "3.2.6rc4",
    )

    skills_root = tmp_path / "doctrine_skills"
    for legacy_name, canonical_name in RETIRED_LEGACY_SKILL_REPLACEMENTS.items():
        _create_skill(skills_root, legacy_name)
        _create_skill(skills_root, canonical_name)
    registry = SkillRegistry(skills_root)

    global_roots = [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
    ]
    custom_skills = []
    for global_root in global_roots:
        for legacy_name in RETIRED_LEGACY_SKILL_REPLACEMENTS:
            _create_skill(global_root, legacy_name, "# stale managed alias\n")
        custom_skill = global_root / "custom-user-skill" / "SKILL.md"
        custom_skill.parent.mkdir(parents=True)
        custom_skill.write_text("# custom user skill\n", encoding="utf-8")
        custom_skills.append(custom_skill)

    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "agent-skills.lock").write_text("3.2.6rc4", encoding="utf-8")
    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    for global_root in global_roots:
        assert all(
            not (global_root / legacy_name).exists()
            for legacy_name in RETIRED_LEGACY_SKILL_REPLACEMENTS
        )
        assert all(
            (global_root / canonical_name / "SKILL.md").is_file()
            for canonical_name in RETIRED_LEGACY_SKILL_REPLACEMENTS.values()
        )
    assert all(
        custom_skill.read_text(encoding="utf-8") == "# custom user skill\n"
        for custom_skill in custom_skills
    )


def test_global_bootstrap_removes_readonly_retired_skill_tree(tmp_path: Path, monkeypatch) -> None:
    from specify_cli.runtime import agent_skills

    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spec-kitty-test-skill")
    registry = SkillRegistry(skills_root)

    retired_skill = home / ".claude" / "skills" / "debugger-debbie" / "SKILL.md"
    retired_skill.parent.mkdir(parents=True, exist_ok=True)
    retired_skill.write_text("# retired\n", encoding="utf-8")
    retired_skill.chmod(0o444)

    real_rmtree = agent_skills.shutil.rmtree

    def windows_like_rmtree(path: str | Path, onerror=None, **kwargs) -> None:
        readonly_files = [file_path for file_path in Path(path).rglob("*") if file_path.is_file() and not file_path.stat().st_mode & 0o200]
        if readonly_files and onerror is None:
            raise PermissionError(readonly_files[0])
        for readonly_file in readonly_files:
            assert onerror is not None

            def remove_after_chmod(path_str: str) -> None:
                target = Path(path_str)
                if not target.stat().st_mode & 0o200:
                    raise PermissionError(path_str)
                target.unlink()

            onerror(remove_after_chmod, str(readonly_file), PermissionError(str(readonly_file)))
        real_rmtree(path, onerror=onerror, **kwargs)

    monkeypatch.setattr(agent_skills.shutil, "rmtree", windows_like_rmtree)
    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    assert not retired_skill.parent.exists()


def test_global_bootstrap_adds_frontmatter_to_plain_skill(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(
        skills_root,
        "spk-start-here",
        "# spk-start-here\n\nGet governance context for an action.\n",
    )
    registry = SkillRegistry(skills_root)

    monkeypatch.setattr(
        "specify_cli.runtime.agent_skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    managed_skill = home / ".agents" / "skills" / "spk-start-here" / "SKILL.md"
    content = managed_skill.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: spk-start-here\n" in content
    assert "description: Get governance context for an action.\n" in content
