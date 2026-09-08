---
work_package_id: WP02
title: Явный и ownership-aware global skill refresh
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
- NFR-001
- NFR-002
- NFR-003
- C-003
- C-004
- C-005
planning_base_branch: codex/global-skill-bootstrap-safety
merge_target_branch: codex/global-skill-bootstrap-safety
branch_strategy: Planning artifacts for this mission were generated on codex/global-skill-bootstrap-safety. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/global-skill-bootstrap-safety unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
create_intent:
- docs/adr/3.x/2026-09-08-1-explicit-global-skill-refresh.md
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/__init__.py
- src/specify_cli/runtime/agent_skills.py
- src/specify_cli/skills/installer.py
- .kittify/metadata.yaml
- pyproject.toml
- uv.lock
- docs/changelog/CHANGELOG.md
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
- docs/adr/3.x/2026-09-08-1-explicit-global-skill-refresh.md
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 - Явный и ownership-aware global skill refresh

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Убрать скрытую запись в user-global skill roots из обычного CLI startup и оставить обновление навыков только за явными install, upgrade или repair flows. Перевести обновление одного canonical skill на ownership-aware overlay: package-owned source paths обновляются, а неизвестные пути внутри существующего skill-каталога сохраняются.

Изменение должно сохранить отдельную политику user-global slash commands, точечную очистку exact retired skills и совместимость с version marker. Обязательная версия пакета повышается из-за изменения `src/specify_cli/__init__.py`, а архитектурное решение и observable behavior фиксируются в ADR и changelog.

Запуск реализации:

```text
spec-kitty agent action implement WP02 --agent codex
```

## Context

Mission: `global-skill-bootstrap-safety-01M20J6C`.

Перед началом проверь, что зависимый WP01 находится в статусе `approved` или `done`. WP01 поставляет acceptance-контракты для ordinary startup, unknown-file preservation, read-only replacement и distribution policy. Реализацию начинай после подтверждения этих тестов и сохраняй red-first дисциплину: тесты WP01 должны быть красными на planning base для исправляемых дефектов и зелёными на финальном состоянии.

Проблемный поток сейчас начинается в `src/specify_cli/__init__.py::main_callback`: обычная команда импортирует и вызывает `ensure_global_agent_skills()`. Дальше `src/specify_cli/runtime/agent_skills.py::_sync_skill_root` удаляет canonical skill directory и копирует packaged tree целиком. Такой startup может создать отсутствующий global root, перепроецировать устаревший marker и удалить пользовательские файлы, которых нет в текущем пакете.

Явный installer в `src/specify_cli/skills/installer.py::_sync_global_skill` повторяет whole-directory replace. Он должен стать единственным низкоуровневым seam для обновления одного canonical skill. Runtime должен делегировать ему обновление, а не поддерживать вторую копию copy/delete алгоритма.

Термины этого WP имеют точный смысл:

- `package-owned path` - файл, присутствующий в source tree синхронизируемого canonical skill;
- `unknown path` - существующий путь внутри destination skill, отсутствующий в текущем source tree;
- `exact source path collision` - destination path с тем же относительным путём, что и source-owned файл;
- `retired skill` - exact имя из `RETIRED_CANONICAL_SKILL_NAMES`, для которого действует отдельная cleanup-политика.

Обязательные границы:

- неизвестные файлы и каталоги сохраняются побайтно и с исходным mode;
- exact collision обновляется в пользу текущего source tree, даже если старый файл read-only;
- symlink или обычный файл, стоящий на месте ожидаемого destination directory, обрабатывается только на exact colliding path и не используется для traversal;
- чужая ветка `codex/spec-kitty-global-bootstrap-scope` только reference: её нельзя checkout, изменять, cherry-pick или интегрировать;
- slash-command startup и `ensure_global_agent_commands()` вне scope этого WP;
- live user-global roots, HOSTKEY, release и публикация не используются для проверки.

Работай только в execution workspace WP02 и предпочитай пути из frontmatter. Не добавляй новые файлы вне `owned_files`; если без малого изменения вне карты нельзя завершить задачу, остановись и доложи parent agent вместо самостоятельного расширения scope.

### Subtask T005: Убрать global skill sync из ordinary root callback и выполнить обязательный version bump

**Purpose**: Сделать обычный root callback read-only относительно global skill roots, сохранив остальные startup gates и отдельный slash-command contract.

**Steps**:

1. Открой `src/specify_cli/__init__.py` и проверь фактический вызов внутри `main_callback` с учётом fast path и doctor path.
2. Удали импорт и вызов `ensure_global_agent_skills()` из ordinary root callback. Не оставляй скрытый вызов через локальный alias, helper или import side effect.
3. Сохрани `ensure_runtime()`, project startup gates, `check_version_pin()` и schema gate в существующем порядке, если они не зависят от удаляемого вызова.
4. Сохрани вызов `ensure_global_agent_commands()` и его doctor-specific исключение. User-global slash-command startup не является частью T005 и не должен измениться.
5. Проверь, что обычная команда с устаревшим `agent-skills.lock` не вызывает registry discovery, не создаёт `~/.kittify` или другой global root и не меняет marker.
6. Проверь, что отсутствие global skill tree также не приводит к его созданию при обычном CLI startup.
7. Обнови `pyproject.toml` обязательным version bump, требуемым изменением `__init__.py`. Сначала прочитай текущую версию и правила проекта; не придумывай отдельную release-схему и не меняй другие package metadata.
8. Не используй старую непубликованную ветку как источник кода. Историческая reference не заменяет текущий source и план.

**Files**:

- `src/specify_cli/__init__.py` - минимальное удаление global skill refresh из callback и сохранение соседних startup checks.
- `pyproject.toml` - обязательное увеличение package version, согласованное с текущей версией и локальной политикой.

**Validation**:

- Запусти targeted acceptance tests WP01 в `tests/runtime/test_bootstrap_unit.py` через изолированные `HOME`, `USERPROFILE` и `SPEC_KITTY_HOME`.
- Отдельно проверь call-site counterfactual: если вызов `ensure_global_agent_skills()` временно вернуть в тестовую копию, ordinary-startup тест должен стать красным. Не оставляй mutation в рабочем дереве.
- Проверь, что regression assertion для `ensure_global_agent_commands()` остаётся зелёной.
- Убедись, что diff показывает только ожидаемое удаление и version bump.

### Subtask T006: Реализовать безопасный overlay в installer

**Purpose**: Заменить destructive whole-directory replace в `src/specify_cli/skills/installer.py::_sync_global_skill` на обновление только package-owned source paths.

**Steps**:

1. Используй `CanonicalSkill.skill_dir` как единственный source tree и вычисляй относительный путь каждого source-owned файла относительно него.
2. Создавай destination root и необходимые source-owned каталоги только в явном install, upgrade или repair flow. Ordinary startup не должен достигать этого seam.
3. При exact source path collision обновляй destination в пользу source. Это правило применяется к `SKILL.md` и ко всем другим source-owned файлам, включая вложенные файлы.
4. Перед заменой read-only source-owned destination временно сделай writable на exact path. После успешной записи снова сними write bits с обновлённого source-owned файла.
5. Если на ожидаемом пути source directory находится destination file или symlink, удали только этот exact colliding path безопасным helper-ом. Если на пути source file находится destination directory или symlink, также разреши только точечную замену этого пути.
6. Не следуй неизвестным symlink paths и не удаляй target, на который они указывают. Для symlink collision работай с самим link path.
7. Не удаляй существующий destination skill directory перед копированием всего дерева. Не используй `copytree` с удалением корня как замену overlay.
8. Unknown files, unknown nested directories и их modes должны остаться без изменения, даже если соответствующего пути нет в новом source tree.
9. Не применяй read-only chmod ко всему destination tree: это может изменить mode unknown files. Read-only режим разрешён только для файлов, реально записанных как package-owned source paths.
10. Нормализацию `SKILL.md` выполняй после source update только для destination `SKILL.md`, принадлежащего текущему source tree. Не читай и не переписывай unknown metadata.
11. Не меняй unrelated skill directories. Existing retired cleanup остаётся отдельной exact-name политикой и не должен превращаться в общий cleanup неизвестных каталогов.
12. Сохрани текущие delivery semantics для project-local projection. T006 касается global canonical destination, а не архивирования пользовательских project-local файлов.

**Files**:

- `src/specify_cli/skills/installer.py` - `_sync_global_skill` и минимальные приватные helpers, необходимые для точечного collision handling и ownership-aware mode handling.

**Validation**:

- Запусти `tests/specify_cli/skills/test_installer.py` из WP01 на temporary HOME и fixture roots.
- Подтверди сохранение неизвестного `agents/openai.yaml`, неизвестного вложенного файла и постороннего skill directory по bytes и mode.
- Подтверди обновление устаревшего package-owned body при сохранении соседнего unknown path.
- Подтверди замену read-only package-owned destination и итоговый read-only mode обновлённого файла.
- Подтверди безопасное поведение для destination symlink/file collision без traversal в неизвестный target.

### Subtask T007: Делегировать runtime обновление в единый seam

**Purpose**: Устранить вторую destructive реализацию в `runtime.agent_skills` и оставить один ownership-aware механизм обновления canonical skill.

**Steps**:

1. В `src/specify_cli/runtime/agent_skills.py` оставь registry discovery, определение installable roots, lock и version-marker orchestration в пределах существующего explicit refresh contract.
2. Замени локальный `copytree` и удаление canonical destination в `_sync_skill_root` делегированием в installer seam `_sync_global_skill` либо в минимальный публичный wrapper над ним.
3. Не дублируй в runtime source-path iteration, read-only chmod, normalization или collision deletion. Эти правила должны иметь один owner в installer.
4. Проверь import direction и циклы. Runtime может использовать canonical installer seam, но не должен импортировать CLI callback для запуска refresh.
5. Сохрани отдельную очистку только exact retired names из `RETIRED_CANONICAL_SKILL_NAMES`. Не удаляй unknown skill paths, не вводи name-based cleanup для обычных canonical directories и не расширяй C-004.
6. После делегирования каждый canonical skill, переданный из registry, должен получить те же overlay semantics, что и explicit installer: source-owned paths обновляются, unknown paths сохраняются, read-only обновление безопасно.
7. Убедись, что version marker и lock не превращаются в новый startup write path. Их orchestration должна выполняться только вызывающим явным flow после T005.
8. Не меняй `ensure_global_agent_commands()` и user-global slash-command roots. Это отдельная surface и acceptance boundary.

**Files**:

- `src/specify_cli/runtime/agent_skills.py` - runtime orchestration и точечный retired cleanup; без второй реализации overlay.
- `src/specify_cli/skills/installer.py` - canonical owner seam из T006, если для совместной делегации нужен минимальный внутренний интерфейс.

**Validation**:

- Запусти `tests/runtime/test_agent_skills.py` с version-marker fixture и изолированным HOME.
- Проверь, что повторный explicit refresh не стирает unknown files при смене marker или runtime package version.
- Проверь static search по runtime module: отсутствие `copytree` и whole-directory removal для обычного canonical skill обновления.
- Проверь, что exact retired cleanup сохраняет прежний scope и не удаляет посторонний skill.

### Subtask T008: Зафиксировать ADR, changelog и observable migration expectation

**Purpose**: Документировать новую ownership boundary и изменение startup behavior в canonical project documentation.

**Steps**:

1. Создай `docs/adr/3.x/2026-09-08-1-explicit-global-skill-refresh.md` по локальному ADR pattern и на русском языке, сохраняя технические identifiers без перевода.
2. В ADR зафиксируй контекст потери пользовательских файлов, решение с explicit refresh и ownership-aware overlay, последствия для package-owned и unknown paths.
3. В ADR явно укажи, что global skills остаются machine-level/user-global surface, но обычный startup больше не является владельцем записи.
4. В ADR явно сохрани принятое решение для user-global slash commands: startup и refresh slash-command roots находятся вне scope этого WP и не получают нового поведения.
5. В ADR опиши exact collision precedence, read-only replacement, symlink safety и отдельный exact-name retired cleanup.
6. Добавь в `docs/changelog/CHANGELOG.md` запись о том, что обычные команды больше не переписывают global skills, а явная синхронизация обновляет package-owned paths и сохраняет unknown paths.
7. В changelog укажи migration expectation: пользователю доступен явный install, upgrade или repair flow для refresh; live installation и release публикация этим WP не выполняются.
8. Не добавляй неподтверждённые claims о wheel inventory, SHA-256 или HOSTKEY. Это scope WP03 и его evidence.

**Files**:

- `docs/adr/3.x/2026-09-08-1-explicit-global-skill-refresh.md` - новый ADR.
- `docs/changelog/CHANGELOG.md` - короткая запись observable behavior и migration expectation.

**Validation**:

- Сверь ADR с `spec.md`, `plan.md` и фактическим diff, чтобы документация не обещала поведения вне WP02.
- Проверь, что в ADR и changelog нет инструкций менять чужую ветку, live root или slash-command startup.
- Выполни проектную проверку кодировки для изменённых markdown-файлов и `git diff --check`.

### Subtask T009: Выполнить targeted quality и ownership checks

**Purpose**: Доказать red-to-green поведение WP02 на изолированных fixtures и закрыть обязательные lint, type, architecture и diff gates.

**Steps**:

1. Проверь dependency gate: WP01 должен быть `approved` или `done`; зафиксируй в handoff, какой acceptance surface использован.
2. Запусти targeted tests `tests/runtime/test_bootstrap_unit.py`, `tests/specify_cli/skills/test_installer.py`, `tests/runtime/test_agent_skills.py` и `tests/doctrine/test_spk_skill_pack.py` в окружении с temporary `HOME`, `USERPROFILE` и `SPEC_KITTY_HOME`.
3. Убедись, что ordinary-startup acceptance фиксирует ноль изменённых файлов, marker и metadata, а отсутствующее global tree не создаётся.
4. Убедись, что explicit-sync acceptance обновляет все exact source collisions и сохраняет 100 процентов unknown fixture files и modes.
5. Выполни counterfactual mutation checks: возврат startup call должен сделать ordinary-startup test красным, а возврат destructive replace должен сделать unknown-preservation test красным. После каждой проверки восстанови рабочее состояние.
6. Запусти `ruff check` по изменённым Python-файлам и исправь найденные проблемы без blanket suppressions.
7. Запусти `mypy --strict` по изменённым модулям через проектную конфигурацию.
8. Запусти `pytest tests/architectural/test_no_legacy_terminology.py` и не добавляй legacy terminology в код или docs.
9. Выполни `git diff --check` и проверь, что изменены только файлы из WP02 `owned_files`.
10. Проверь, что `src/specify_cli/__init__.py` действительно получил version bump в `pyproject.toml`, а changelog и ADR отражают тот же observable contract.
11. Не запускай full release, wheel delivery, HOSTKEY plan execution, live install, cleanup или scheduler. Artifact identity и dry delivery относятся к WP03.

**Files**:

- Проверяются только файлы из frontmatter и тестовые surfaces WP01; новые тестовые файлы в WP02 не создавай без отдельного согласования ownership.

**Validation**:

- Все targeted tests и перечисленные quality gates зелёные либо имеют явно зафиксированную baseline причину, подтверждённую сравнением с planning base.
- Diff не содержит записи в настоящий user-global root и не содержит изменений в чужой ветке.
- Handoff перечисляет команды, exit codes, red-to-green evidence и оставшиеся ограничения без утверждения о WP03.

## Definition of Done

- [ ] WP01 подтверждён как `approved` или `done`, а его acceptance tests использованы как входной контракт.
- [ ] `main_callback` больше не вызывает `ensure_global_agent_skills()` на ordinary startup и не импортирует его для этого пути.
- [ ] `ensure_runtime()`, project gates и `ensure_global_agent_commands()` сохранили требуемое поведение; slash-command startup не изменён.
- [ ] `pyproject.toml` содержит обязательный version bump для изменения `src/specify_cli/__init__.py`.
- [ ] `_sync_global_skill` выполняет overlay только source-owned paths и не удаляет destination skill directory целиком.
- [ ] Exact source path collisions обновляются, в том числе поверх read-only file, после чего source-owned files получают read-only mode.
- [ ] Unknown files, nested unknown directories, symlink targets и посторонние skill directories сохраняются с исходными bytes и mode.
- [ ] Runtime использует единый installer seam; второй destructive copy/delete algorithm удалён.
- [ ] Retired cleanup ограничен exact именами из `RETIRED_CANONICAL_SKILL_NAMES` и не превращён в общий cleanup.
- [ ] ADR и changelog описывают фактический startup boundary, ownership policy и migration expectation на русском языке.
- [ ] Targeted pytest, mutation checks, ruff, mypy, architecture test и `git diff --check` выполнены на изолированных fixtures.
- [ ] Изменены только `owned_files` этого WP; чужая ветка остаётся только read-only reference.
- [ ] В handoff есть проверяемые команды и ограничения; нет claims о live delivery или WP03 evidence.

Результат каждого T005-T009 должен быть отмечен через штатный event-sourced status механизм Spec Kitty, а не только через локальные checkbox. Команду реализации для воспроизводимого запуска использовать ровно в таком виде:

```text
spec-kitty agent action implement WP02 --agent codex
```

## Risks

- Удаление только вызова в callback может случайно затронуть runtime bootstrap. Сравни порядок соседних startup checks и закрепи regression test.
- Overlay может скрыто chmod-ить unknown files. Храни явный список записанных source-owned paths и проверяй mode до и после.
- Symlink collision может привести к traversal. Работай только с exact link path и не следуй unknown target.
- Дублирование seam в runtime вернёт две расходящиеся политики. Reviewer должен искать остаточные `copytree`, broad `rmtree` и normalization в runtime module.
- Version marker может снова стать скрытым write path. Проверяй call graph ordinary startup и запускай тесты с отсутствующим и устаревшим marker.
- Exact retired cleanup может быть расширен эвристикой по имени. Сохраняй только существующий explicit allowlist и документируй C-004.
- ADR или changelog могут случайно обещать slash-command migration, release или HOSTKEY действие. Сверяй scope с `spec.md`, `plan.md` и WP03.
- Изменение настоящего HOME недопустимо. Все mutation tests должны использовать temporary environment variables и fixture roots.

## Reviewer Guidance

Проверь сначала observable boundary: обычный CLI startup с устаревшим marker и отсутствующим tree должен завершаться без записи. Отдельно проверь, что slash-command startup и `ensure_global_agent_commands()` остались неизменными.

Затем проверь ownership proof в installer. Для каждого source-owned path ожидается обновление; для каждого unknown path ожидается сохранение bytes и mode. Особое внимание удели nested unknown path, read-only destination, file/directory collision и symlink collision.

Проверь, что runtime действительно делегирует в один canonical installer seam, а не сохраняет вторую реализацию под другим helper name. Retired cleanup должен быть exact-name и отдельным контрактом.

Сверь version bump с фактическим изменением `__init__.py`. Сверь ADR и changelog с кодом и acceptance evidence; не принимай формулировки о distribution artifact или dry delivery как доказательство WP02.

Проверь red-to-green mutation evidence, targeted test commands, изолированный HOME, `ruff`, `mypy`, architecture gate и `git diff --check`. Убедись, что diff ограничен frontmatter `owned_files`, а ветка `codex/spec-kitty-global-bootstrap-scope` не была изменена или интегрирована.

Критерий готовности: WP02 можно передать на review только когда startup boundary, overlay ownership, single seam, документация и все проверки подтверждены фактическим diff и исполняемыми результатами.
