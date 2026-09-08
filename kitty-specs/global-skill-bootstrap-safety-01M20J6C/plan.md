# План реализации: Безопасный глобальный bootstrap навыков

## Цель

Закрыть повторяющийся класс потери пользовательских файлов в user-global skill roots. Обычный CLI startup перестаёт быть владельцем записи. Явные install, upgrade и repair flows продолжают обновлять package-owned файлы, но не удаляют неизвестные соседние файлы. Собранный wheel должен содержать explicit-only metadata для legacy program skill.

## Текущее устройство и дефект

`src/specify_cli/__init__.py::main_callback` вызывает `ensure_global_agent_skills()` перед большинством обычных команд. `src/specify_cli/runtime/agent_skills.py::_sync_skill_root` удаляет каждый существующий canonical skill-каталог и копирует packaged tree. Общий marker учитывает только версию пакета. Поэтому разные runtime могут по очереди перепроецировать один `HOME` и уничтожать файлы, отсутствующие в текущем пакете.

`src/specify_cli/skills/installer.py::_sync_global_skill` повторяет тот же destructive replace во время явной установки. Этот путь должен соблюдать charter boundary: неизвестный путь без доказанного package ownership сохраняется.

## Целевая архитектура

```mermaid
flowchart LR
    A[Обычная команда CLI] --> B[Runtime checks]
    B --> C[Без записи в global skill roots]
    D[Явный init, upgrade или repair] --> E[Canonical package registry]
    E --> F[Безопасное overlay-обновление]
    F --> G[Обновлены package-owned файлы]
    F --> H[Сохранены неизвестные файлы]
```

### Владение

- `main_callback` владеет только безопасными startup checks и больше не запускает global skill refresh.
- `_sync_global_skill` становится единственным низкоуровневым владельцем обновления одного canonical skill.
- Явные `init`, `upgrade` и `repair` flows достигают этого владельца через `install_skills_for_agent()` или `install_all_skills()`; недостижимый после удаления startup-вызова `runtime.agent_skills` удаляется.
- Exact-name cleanup retired skills остаётся в installer и не расширяется до неизвестных каталогов.
- Package source владеет файлами, присутствующими в source tree текущего skill.
- Existing destination paths, отсутствующие в source tree, считаются неизвестными и сохраняются.
- Exact collision по пути source-owned файла разрешается в пользу source: read-only файл временно делается writable, обновляется и снова защищается.

## Изменения по файлам

### Контракт startup

- `src/specify_cli/__init__.py`
  - удалить вызов `ensure_global_agent_skills()` и его импорт из обычного root callback;
  - оставить runtime bootstrap, version pin gates и slash-command behavior без изменений.
- `tests/runtime/test_bootstrap_unit.py`
  - acceptance test через root callback: обычная команда не вызывает global skill sync;
  - сохранить доказательство, что остальные startup checks продолжают вызываться.

### Контракт безопасной синхронизации

- `src/specify_cli/skills/installer.py`
  - заменить whole-directory replace на overlay только source paths;
  - безопасно обработать destination symlink/file collisions;
  - повторно сделать скопированные source-owned файлы read-only;
  - сохранить неизвестные файлы и каталоги.
- `tests/specify_cli/skills/test_installer.py`
  - red-first tests для неизвестной metadata, read-only replacement, вложенного unknown path и постороннего skill.
- `src/specify_cli/runtime/agent_skills.py` и `tests/runtime/test_agent_skills.py`
  - удалить недостижимый legacy bootstrap и его прямые тесты после переноса observable контрактов на startup и installer surfaces.
- `tests/architectural/test_no_dead_modules.py`
  - подтвердить отсутствие нового orphan module после удаления startup-вызова.

### Контракт дистрибутива

- `tests/doctrine/test_spk_skill_pack.py`
  - проверить source path `src/charter/offering/skills/spec-kitty-program-orchestrate/agents/openai.yaml`;
  - разобрать YAML и потребовать `allow_implicit_invocation: false`;
  - отдельная wheel verification после build проверяет соответствующий import path без src-layout prefix: `charter/offering/skills/spec-kitty-program-orchestrate/agents/openai.yaml`.
- `pyproject.toml`
  - выполнить обязательный version bump для изменения `src/specify_cli/__init__.py`.
- `docs/changelog/CHANGELOG.md`
  - описать observable behavior и migration expectation.
- `docs/adr/3.x/2026-09-08-1-explicit-global-skill-refresh.md`
  - зафиксировать, что global skills остаются machine-level, но refresh становится явным и ownership-aware;
  - не менять принятое решение для user-global slash commands.

## ATDD и порядок коммитов

1. Добавить acceptance tests для ordinary startup, unknown-file preservation и distribution metadata.
2. Запустить их на planning base и сохранить ожидаемое падение по двум исходным дефектам. Metadata-test может быть зелёным на base из-за уже слитого PR #16; его mutation check должен доказать oracle.
3. Закоммитить только тесты отдельным red-first commit.
4. Реализовать startup boundary и безопасный overlay.
5. Добавить ADR, changelog и version bump.
6. Выполнить targeted tests, mutation checks, ruff, mypy и релевантные architectural gates.
7. Собрать wheel из финального task head, записать SHA-256 и проверить inventory.
8. Создать draft PR, дождаться CI, выполнить самостоятельное ревью и перевести PR в ready только при зелёных обязательных checks.
9. Подготовить HOSTKEY dry plan с текущими CAS fingerprints и artifact identity. Ничего не устанавливать.

## Риски и меры

| Риск | Мера |
|------|------|
| Скрытое изменение slash commands | Не менять `ensure_global_agent_commands()`; отдельный regression test сохраняет его вызов. |
| Сохранение устаревшего package-файла | Сохранять только пути, которых нет в текущем source tree; совпадающие source paths всегда обновлять. |
| Symlink traversal | Удалять только exact colliding symlink/file и не следовать неизвестным symlink paths. |
| Read-only destination | Делать writable только exact source-owned destination перед заменой. |
| Mixed-runtime повтор | Обычный startup больше не запускает skill sync; артефакт получает отдельную identity. |
| Случайная запись в настоящий HOME | Все CLI и fixture tests запускаются с изолированными `HOME`, `USERPROFILE` и `SPEC_KITTY_HOME`. |
| Старая непубликованная ветка | Не изменять и не интегрировать её; использовать только как историческую справку. |

## Проверки

- Targeted pytest для runtime bootstrap, skill installer и packaged policy.
- Counterfactual mutation: удалить вызов-защиту либо инвертировать policy и убедиться, что соответствующий тест падает.
- `ruff check` для изменённых Python-файлов.
- `mypy --strict` для изменённых модулей через проектную конфигурацию.
- `pytest tests/architectural/test_no_legacy_terminology.py`.
- `git diff --check`.
- Wheel build и zip-level проверка exact metadata.
- HOSTKEY read-only snapshot и локальная валидация dry plan.

## Согласованная post-accept delta: fork runner fallback

После полного product CI единственный `Check Shared Package Drift` оставался в очереди без runner: оба job были жёстко привязаны к `blacksmith-4vcpu-ubuntu-2404`, недоступному в fork. Руслан отдельно разрешил исправить этот blocker и после зелёного CI завершить merge-пакет.

- В `.github/workflows/check-spec-kitty-events-alignment.yml` оба `runs-on` используют тот же repository-aware выбор, что и соседние PR workflows: Blacksmith в `Priivacy-ai/spec-kitty`, `ubuntu-latest` в fork.
- Проверка включает YAML parse, точное наличие двух fallback expressions и реальный PR run обоих jobs.
- После полного green допустимы draft → ready, merge PR #21 и безопасный cleanup только task-owned worktree/ветки.
- Release publication, live install, HOSTKEY upload, restart и scheduler mutation остаются вне scope.

## Delivery gates

- Source PR можно открыть и довести до ready после зелёных проверок.
- После полного CI green разрешены ready и merge PR #21 с последующим безопасным cleanup task-owned worktree/ветки.
- GitHub/PyPI release не выполняется.
- HOSTKEY install, cleanup и scheduler остаются вне этой Mission.
