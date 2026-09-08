---
work_package_id: WP01
title: Acceptance-контракты безопасного global skill refresh
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: codex/global-skill-bootstrap-safety
merge_target_branch: codex/global-skill-bootstrap-safety
branch_strategy: Planning artifacts for this mission were generated on codex/global-skill-bootstrap-safety. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/global-skill-bootstrap-safety unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/runtime/test_bootstrap_unit.py
- tests/specify_cli/skills/test_installer.py
- tests/doctrine/test_spk_skill_pack.py
role: implementer
tags: []
tracker_refs: []
---

# WP01: Acceptance-контракты безопасного global skill refresh

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Закрепить независимые acceptance-контракты для безопасного обновления глобальных навыков до изменения реализации. Тесты должны сначала воспроизвести RED на planning base: обычный startup не должен вызывать global skill refresh, явная синхронизация должна сохранять неизвестные пользовательские пути, а дистрибутивная policy должна требовать explicit-only metadata. После этого WP02 сможет перевести те же контракты в GREEN изменением только разрешённых product surfaces.

## Context

Mission закрывает повторяющееся удаление пользовательских файлов из user-global skill roots. В текущем коде `src/specify_cli/__init__.py::main_callback` импортирует и вызывает `ensure_global_agent_skills()` при обычном запуске, а `src/specify_cli/runtime/agent_skills.py::_sync_skill_root` удаляет существующий canonical skill-каталог целиком перед копированием packaged tree. Поэтому acceptance-контракты должны проверять наблюдаемое содержимое, режимы файлов и отсутствие записи, а не только вызовы моков.

WP01 владеет только тестовыми файлами из frontmatter. WP02 зависит от этих контрактов и изменяет startup boundary и ownership-aware overlay; WP03 отдельно проверит собранный immutable артефакт и delivery evidence. Не меняй `spec.md`, `plan.md`, `wps.yaml`, product code, metadata источника, wheel-процесс или live skill roots в рамках этого WP.

Канонические ожидания следующие:

- Обычная команда чтения состояния или работы с Mission не вызывает global skill sync.
- При обычном startup существующий global skill tree, устаревший marker, bytes, modes и времена записи не меняются.
- При отсутствии global skill tree обычный startup не создаёт его автоматически.
- Явная синхронизация обновляет package-owned paths из source tree.
- Явная синхронизация сохраняет неизвестные файлы и каталоги внутри существующего canonical skill побайтно и с исходным mode.
- Посторонний skill с другим canonical name не меняется.
- Read-only package-owned destination обновляется и после записи снова остаётся read-only.
- Exact metadata `src/charter/offering/skills/spec-kitty-program-orchestrate/agents/openai.yaml` существует и после YAML-разбора содержит `policy.allow_implicit_invocation == false`.

Все fixture paths должны жить под `tmp_path`. Для сценариев, использующих глобальные roots, переопредели `Path.home()` либо соответствующий path seam и задай изолированные `HOME`, `USERPROFILE` и `SPEC_KITTY_HOME`, если это требуется текущими helper-ами. Не допускай чтения или записи настоящего user-global каталога.

### Subtask T001: Red startup contract for ordinary commands

**Purpose**: Зафиксировать FR-001 и NFR-001: обычная команда не владеет записью в global skill roots, даже если установленная версия и marker расходятся.

**Steps**:

1. Добавь acceptance test в `tests/runtime/test_bootstrap_unit.py` рядом с существующим классом `TestVersionPinWiredIntoCallback`, чтобы проверка проходила через `main_callback`, а не через внутреннюю функцию синхронизации.
2. Назови тест так, чтобы из имени было видно observable behavior, например `test_main_callback_does_not_sync_global_skills_for_ordinary_command`.
3. Подготовь `tmp_path / "home"` и canonical root внутри него. Создай существующий skill, sentinel-файл и marker `agent-skills.lock` со старой версией.
4. Сохрани до запуска snapshot: относительные пути, bytes, `st_mode` и `st_mtime_ns` всех файлов и каталогов в fixture tree.
5. Отдельно подготовь сценарий с отсутствующим global skill root либо параметризуй тест, чтобы отсутствие дерева было явно проверено и не сводилось к проверке уже созданного каталога.
6. Задай обычную argv-форму команды чтения состояния, например `status` с безопасным `--json`, без `init`, `upgrade`, `repair` или явного install flow.
7. Замокай только внешние startup-зависимости, необходимые для детерминированного вызова: `ensure_runtime`, `root_callback`, поиск project root и unrelated project gates. Не подменяй сам acceptance seam так, чтобы тест мог пройти при фактическом вызове global sync.
8. Установи `ensure_global_agent_skills` в mock, который позволяет зафиксировать вызов, и проверь `assert_not_called()` после `main_callback(...)`.
9. Проверь, что допустимые runtime checks и project safety gates сохраняются, если это уже зафиксировано соседними тестами; отсутствие skill sync не должно отменять `ensure_runtime`, `ensure_global_agent_commands` или `check_version_pin` там, где они положены по argv.
10. Для snapshot-сценария дополнительно сравни bytes, mode и `mtime_ns` до и после callback. Проверяй отсутствие новых путей, а не только неизменность sentinel.
11. Для отсутствующего root проверь `not root.exists()` после callback. Не создавай root через fixture teardown или вызов helper-а до самой проверяемой команды.
12. Не привязывай контракт к конкретному выводу баннера или к внутреннему порядку импортов. Контрактом является отсутствие записи и отсутствие вызова `ensure_global_agent_skills`.
13. Убедись, что тест не запускает реальный callback до установки всех isolation seams: текущий planning base действительно пишет global skills при ordinary startup.
14. В комментарии теста свяжи проверку с FR-001, NFR-001 и Сценарием 1 из `spec.md`; не копируй весь текст спецификации в код.

**Files**: `tests/runtime/test_bootstrap_unit.py` - один acceptance test либо небольшая параметризация в существующем callback test class; не добавляй новый production helper.

**Validation**:

- На planning base тест должен быть RED, потому что `main_callback` сейчас вызывает `ensure_global_agent_skills()` после `ensure_runtime()`.
- Если реализация уже изменена в рабочем дереве, сначала проверь RED на чистой planning base, затем вернись к текущему task head без отмены чужих изменений.
- После WP02 этот тест обязан стать GREEN при сохранении проверок snapshot и отсутствующего root.
- Mutation check: временно верни вызов `ensure_global_agent_skills()` в тестируемый callback в disposable копии или эквивалентном counterfactual и убедись, что `assert_not_called()` снова краснеет.

### Subtask T002: Red tests for unknown-file preservation and safe replacement

**Purpose**: Закрепить FR-003, FR-004, NFR-002 и NFR-003 для явного install/sync seam, который WP02 будет переводить с whole-directory replace на ownership-aware overlay.

**Steps**:

1. Добавь тесты в `tests/specify_cli/skills/test_installer.py`, используя существующие `_make_skill`, `install_skills_for_agent`, `CanonicalSkill` и pytest fixtures.
2. В каждом тесте отделяй source tree (`skills_src`) от изолированного глобального root под `tmp_path`. Для `codex` используй shared root `.agents/skills`, если это соответствует текущей конфигурации; для native root можно использовать `claude`.
3. Переопредели `Path.home()` или публичный path seam до первого вызова `install_skills_for_agent`, чтобы `_sync_global_skill` не мог попасть в настоящий HOME.
4. Сначала выполни одну штатную установку canonical skill. Затем создай внутри `global_root / skill_name` неизвестный файл `agents/openai.yaml` с уникальными bytes и явным mode.
5. Повтори ту же явную синхронизацию с source tree, где `agents/openai.yaml` отсутствует. Проверь, что unknown file существует, его bytes совпадают побайтно, а mode не изменился.
6. Добавь отдельный вложенный unknown path, например `references/user-notes/custom.md`, причём один или несколько parent directories должны отсутствовать в текущем source tree. После sync проверь весь путь, bytes и mode.
7. Проверь, что package-owned `SKILL.md` с устаревшим содержимым обновляется новым source-содержимым при повторной синхронизации. Это различает ownership-aware overlay от полного no-op.
8. Для read-only варианта перед повторной синхронизацией сними `stat.S_IWRITE` с package-owned destination. После sync проверь новые bytes и отсутствие write-битов; обработка должна быть ограничена exact source-owned path.
9. Создай в том же global root отдельный `third-party` skill с собственным `SKILL.md`, unknown metadata и mode snapshot. После sync canonical skill должен обновиться, а весь посторонний skill - остаться неизменным.
10. Если текущие helper-ы позволяют без platform-specific нестабильности, добавь red-проверки exact collision, когда destination canonical path является symlink или обычным файлом вместо каталога. Проверяй, что тест не следует по unknown symlink и не удаляет соседние paths.
11. Для каждого сценария собери snapshot путей, bytes и mode до второго вызова. Не ограничивайся `exists()`: такой oracle не поймает подмену содержимого или chmod неизвестного файла.
12. Не используй широкое `shutil.rmtree` в тестах для подготовки повторного запуска; fixture должен моделировать пользовательское состояние, которое implementation обязана сохранить.
13. Не переиспользуй уже существующий тест проектной projection как доказательство global ownership: он проверяет `.claude`/`.agents` внутри `project`, тогда как этот контракт должен наблюдать canonical global skill root.
14. Привяжи тестовые docstrings к Сценарию 2 и перечисли, какой path является package-owned, а какой unknown. Это поможет reviewer отличить намеренное обновление от потери пользовательского файла.
15. Сохрани все новые тесты в одном тестовом файле из frontmatter и не меняй `_make_skill`, installer implementation или retired registry.

**Files**: `tests/specify_cli/skills/test_installer.py` - четыре узких acceptance tests либо параметризованный набор с отдельными assertion blocks для metadata, nested path, read-only replacement и unrelated skill.

**Validation**:

- На planning base unknown metadata и вложенный unknown path должны исчезать из-за текущего `shutil.rmtree`/`copytree`; соответствующие тесты обязаны быть RED.
- Read-only replacement должен давать наблюдаемую ошибку или неверный результат на base, если текущая реализация не умеет безопасно обновлять exact owned path.
- Тест постороннего skill должен доказать отсутствие изменений не только canonical directory, но и соседнего canonical name.
- После WP02 все тесты должны стать GREEN без ослабления bytes/mode assertions.
- Mutation check: временно вернуть whole-directory removal либо заменить source path на удаление unknown fixture в disposable варианте и убедиться, что каждый relevant oracle падает.

### Subtask T003: Distribution metadata oracle and mutation proof

**Purpose**: Закрепить FR-005 и NFR-004 так, чтобы legacy program skill не мог вернуться к implicit invocation через неполный или неверный packaged metadata path.

**Steps**:

1. Расшири `tests/doctrine/test_spk_skill_pack.py`, сохранив существующие проверки registry completeness и legacy aliases.
2. Зафиксируй exact path `SKILLS_ROOT / "spec-kitty-program-orchestrate" / "agents" / "openai.yaml"`; не ищи файл по glob, имени directory или первому совпадению.
3. Добавь assertion `metadata_path.is_file()` с сообщением, которое показывает exact relative path при отсутствии файла.
4. Разбери содержимое YAML parser-ом, принятым проектом, вместо substring-поиска. Ожидаемая форма текущего metadata - mapping `policy` с ключом `allow_implicit_invocation`.
5. Проверь, что разобранное значение строго равно `False`, а не truthiness-проверке, строке `"false"` или отсутствующему ключу. При необходимости проверь тип boolean отдельно.
6. Убедись, что oracle не считает наличие legacy skill в обычном registry discovery достаточным доказательством поставки compatibility metadata.
7. Сохрани тест source inventory отдельным от будущей проверки wheel: сборка wheel и SHA-256 принадлежат WP03, поэтому T003 не создаёт артефакты и не меняет delivery evidence.
8. Добавь локальный helper только если он делает exact path и nested policy reusable; не вводи новую production abstraction и не меняй `SkillRegistry` ради теста.
9. Выполни mutation proof в безопасной disposable форме. Скопируй metadata в `tmp_path`, замени значение на `true`, удали файл либо убери nested key и пропусти тот же parser/oracle через временный путь.
10. Зафиксируй, что counterfactual с `true`, отсутствующим файлом и отсутствующим ключом краснеет. Не мутируй tracked source file без обратимого изолированного копирования.
11. Отдельно отметь ожидаемую особенность из `plan.md`: source metadata test может быть GREEN уже на planning base из-за ранее слитого PR #16. В этом случае green не засчитывает отсутствие работы без mutation proof.
12. Проверь, что exact source path и значение policy сохраняются после любого рефакторинга теста. Не заменяй assertion на проверку только `SkillRegistry.get_skill(...)`.
13. В docstring укажи Сценарий 3, exact path и причину explicit-only policy; не добавляй version number или release gate в acceptance test.

**Files**: `tests/doctrine/test_spk_skill_pack.py` - exact source metadata test и минимальный counterfactual helper/тест, без изменения `src/charter/offering/skills/` и без wheel output.

**Validation**:

- На base тест либо красный из-за отсутствующего файла/неверной формы, либо честно зелёный по причине уже существующей metadata; результат должен быть классифицирован, а не скрыт.
- Mutation `allow_implicit_invocation: true` обязана делать oracle RED.
- Mutation удаления exact file или nested key обязана делать oracle RED.
- После WP02/WP03 source и wheel-level checks должны согласованно требовать explicit-only значение.

### Subtask T004: Planning-base run and expected RED record

**Purpose**: Выполнить весь red-first цикл для T001-T003 на planning base и оставить проверяемый журнал того, что именно было RED, что было baseline-green и почему.

**Steps**:

1. Перед запуском зафиксируй current branch, `git status --short` и список изменённых файлов. Допустимы только три тестовых файла WP01; чужие изменения не отменяй и не включай в commit.
2. Убедись, что implementation changes из WP02 отсутствуют в planning-base snapshot. Тесты должны наблюдать текущий дефект, а не заранее замоканный GREEN.
3. Запусти targeted runtime contract с изолированными переменными окружения:
   `python -m pytest tests/runtime/test_bootstrap_unit.py -k "global_skills or ordinary_command or no_global_skill" -q`.
4. Запусти installer contracts:
   `python -m pytest tests/specify_cli/skills/test_installer.py -k "unknown or nested or readonly or third_party or preserve" -q`.
5. Запусти metadata contract:
   `python -m pytest tests/doctrine/test_spk_skill_pack.py -k "program_orchestrate or implicit_invocation or policy" -q`.
6. Если выбранные `-k` выражения не совпадают с окончательными именами тестов, запусти каждый файл целиком и зафиксируй точные node ids. Не делай одинаковый безрезультатный повтор без изменения входных данных.
7. Для каждого failure запиши node id, короткий symptom, ожидаемую причину из текущей реализации и требование/сценарий, который он защищает. Не называй unrelated baseline failure дефектом WP01.
8. Для T001 ожидай RED на текущем вызове `ensure_global_agent_skills()` из `main_callback`; для T002 ожидай потерю unknown paths от destructive replace; для T003 допускай baseline GREEN и требуй mutation proof.
9. Повтори T003 counterfactual mutation в disposable copy и запиши, какие mutations сделали тест красным. Это обязательная защита от vacuous oracle.
10. Выполни `git diff --check` для тестового diff. Не запускай настоящий CLI против user-global HOME и не создавай live skill roots.
11. Отдельно укажи, если environment-specific mode assertion требует адаптации Windows/POSIX. Адаптация должна сохранять проверку ownership и не превращать mode в необязательный.
12. После фиксации RED не исправляй product code в этом WP. Красные тесты должны быть закоммичены отдельным red-first commit до реализации WP02, согласно ATDD contract.
13. В status/review evidence укажи команды, timestamp, planning-base identity и итоговую классификацию. Не создавай дополнительный evidence-файл: owned surface WP01 ограничен `tests/`.
14. Перед завершением проверь, что тестовый diff не затронул `spec.md`, `plan.md`, `wps.yaml`, source metadata, wheel, docs или live paths.

**Files**: только три тестовых файла из frontmatter; T004 не добавляет артефакты и не редактирует mission planning files.

**Validation**:

- Все тесты T001-T003 собраны и запускаются на planning base.
- Ожидаемые RED и baseline-green случаи записаны с node ids и причиной.
- Mutation proof для T003 зафиксирован и показывает настоящий RED при неверной policy.
- `git diff --check` проходит для самого test diff, даже если targeted pytest намеренно красный.
- Red-first commit содержит только acceptance tests и не содержит реализации WP02.

## Definition of Done

- [ ] Frontmatter остаётся валидным и содержит `WP01`, пустые `dependencies`, все requirement refs/subtasks/owned files, `authoritative_surface: "tests/"`, `execution_mode: "code_change"`, `agent_profile: "implementer-ivan"`, `role: "implementer"`, `agent: "codex"` и пустой `model`.
- [ ] `## ⚡ Do This First: Load Agent Profile` остаётся первым body-разделом после H1 и содержит точные profile, role и agent/tool.
- [ ] T001 проверяет ordinary startup через `main_callback`, отсутствие global skill sync, неизменность snapshot и отсутствие создания root.
- [ ] T002 проверяет unknown metadata, вложенный unknown path, обновление read-only package-owned файла и сохранение постороннего skill.
- [ ] T003 проверяет exact source metadata path, YAML boolean `policy.allow_implicit_invocation == false` и non-vacuous mutation behavior.
- [ ] T004 выполняет targeted pytest на planning base, классифицирует RED/baseline-green и фиксирует timestamp, commands и node ids в status/review evidence.
- [ ] Все тестовые fixture paths изолированы через `tmp_path` и patched HOME seams; настоящий user-global каталог не читается и не меняется.
- [ ] Красные acceptance tests оформлены отдельным red-first commit до любых implementation commits.
- [ ] Для каждого Txxx отправлена event-sourced отметка `spec-kitty agent tasks mark-status Txxx --status done` после приложенного evidence; checkbox сам по себе не является доказательством.
- [ ] `git diff --check` проходит, а изменённые пути совпадают только с frontmatter `owned_files`.

Команда запуска реализации WP:

```bash
spec-kitty agent action implement WP01 --agent codex
```

## Risks

- **Ложный GREEN startup-теста.** Если тест мокает вызывающую функцию после её импорта неправильным module path, он может не увидеть вызов. Устанавливай patch на module seam до вызова `main_callback` и добавляй snapshot.
- **Смешение project projection и global ownership.** Проверка только `.agents/skills` внутри `project` не доказывает сохранение canonical global root. T002 обязан наблюдать `Path.home()`-derived root.
- **Вакуозный metadata oracle.** Проверка имени skill или substring `false` пропустит неверный YAML. Требуются exact path, parser, nested key и mutation с `true`/missing key.
- **Запись в настоящий HOME.** Неполный monkeypatch может запустить `_unique_global_roots()` на реальной машине. Все global-root тесты сначала задают isolation seams и после вызова проверяют путь fixture.
- **Нестабильный mode на Windows.** Учитывай `stat.S_IWRITE`, но не отменяй проверку read-only результата и сохранения unknown mode.
- **Подмена baseline failure.** Metadata уже может быть зелёным из-за PR #16. Это не отменяет mutation proof; unrelated failure нельзя приписывать WP01 без cross-base evidence.
- **Расширение scope.** Не добавляй wheel builder, version bump, changelog, ADR, runtime implementation или retired cleanup implementation. Эти поверхности принадлежат другим WP или явно исключены Mission.

## Reviewer Guidance

Reviewer должен проверить diff против frontmatter и убедиться, что acceptance contracts добавлены в три разрешённых файла без product changes. Отдельно проследи, что T001 идёт через `main_callback`, T002 наблюдает canonical global root, а T003 читает exact metadata path и nested boolean.

Проверь red-first evidence на planning base: текущий вызов startup sync должен быть пойман, destructive whole-directory behavior должен ломать preservation tests, а уже зелёный metadata oracle должен иметь mutation proof. Сверь node ids, команды и timestamp с recorded status evidence; не принимай общий отчёт «тесты падали» без причины каждого контракта.

Проверь независимость oracle-ов: bytes, modes, отсутствие новых paths и сохранение third-party skill должны сравниваться до/после; `exists()` и `mock.assert_not_called()` по отдельности недостаточны. Убедись, что fixtures не используют настоящий HOME и что тесты не маскируют дефект чрезмерным mocking.

До передачи WP02 убедись, что red-first commit содержит только тесты, `git diff --check` чист, mutation T003 действительно краснеет при `allow_implicit_invocation: true`, а scope C-001/C-002/C-003/C-004 не нарушен. После implementation WP02 эти же tests должны стать GREEN без ослабления acceptance assertions.
