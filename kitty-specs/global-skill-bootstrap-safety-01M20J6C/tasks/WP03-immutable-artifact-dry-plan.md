---
work_package_id: WP03
title: Неизменяемый артефакт и dry delivery plan
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- NFR-004
- C-001
- C-002
planning_base_branch: codex/global-skill-bootstrap-safety
merge_target_branch: codex/global-skill-bootstrap-safety
branch_strategy: Planning artifacts for this mission were generated on codex/global-skill-bootstrap-safety. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/global-skill-bootstrap-safety unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
history: []
agent_profile: researcher-robbie
authoritative_surface: kitty-specs/global-skill-bootstrap-safety-01M20J6C/
create_intent:
- kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json
execution_mode: planning_artifact
owned_files:
- kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json
role: researcher
tags: []
tracker_refs: []
---

# WP03 - Неизменяемый артефакт и dry delivery plan

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `researcher-robbie`
- **Role**: `researcher`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Подтвердить, что результат WP02 можно передать как воспроизводимый и
неизменяемый distribution artifact, не выполняя публикацию или live-применение.
Собрать проверяемые сведения о wheel, его точном содержимом, source commit,
версии и SHA-256, затем оформить draft PR/CI и локальный HOSTKEY dry plan с
ожидаемым состоянием и CAS-защитами в единственном файле
`kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json`.

## Context

WP03 следует за WP02 и использует его итоговый task head. WP02 должен уже
удалить скрытый startup refresh, заменить destructive replace на ownership-aware
overlay и добавить explicit-only metadata для legacy program skill.

Предметная граница этого WP - доказательства доставки и планирование. Исходный
код, тесты, `pyproject.toml`, changelog, ADR и чужие planning artifacts не
редактируются. Единственный разрешённый создаваемый файл -
`kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json`.

Критическая metadata в wheel должна находиться по точному пути
`src/charter/offering/skills/spec-kitty-program-orchestrate/agents/openai.yaml`.
Разобранное значение `allow_implicit_invocation` обязано быть boolean `false`.
Артефакт должен иметь отдельную runtime identity: версию пакета, commit, из
которого он собран, и SHA-256 самого wheel. Данные нельзя подменять значением
из старого отчёта или из другой ветки.

План доставки является dry-run evidence. Он описывает, что оператор мог бы
проверить на HOSTKEY при совпадении текущего состояния, но не устанавливает
wheel, не удаляет skill-каталоги, не меняет scheduler и не запускает cleanup.
Публикация в PyPI, GitHub Release или другой registry также запрещена.

Все команды выполняются в task-owned checkout и с явным указанием рабочей
директории. Настоящие user-global skill roots и настоящий `HOME` не читаются и
не меняются для fixture-проверок; при необходимости используется временное
изолированное окружение. Секреты, токены, содержимое credential-файлов и
закрытые payloads в evidence не записываются.

## Обязательные границы

1. Не менять файлы, кроме указанного `delivery-evidence.json`.
2. Не вносить исправления в WP02, даже если обнаружена проблема в коде.
3. Не делать `git merge`, `git rebase`, `git reset`, `git clean` или force push.
4. Не публиковать wheel и не загружать его на HOSTKEY.
5. Не запускать live install, uninstall, cleanup, scheduler или restart.
6. Не утверждать зелёный gate без сохранённой команды и её фактического вывода.
7. Не считать dry plan выполненным применением: план должен оставаться
   неисполняемым без отдельного операторского решения и CAS-проверки.

### Subtask T010: Собрать wheel без публикации

**Purpose**: получить wheel из фактического финального task head WP02 и
зафиксировать его идентичность, не создавая release или registry side effect.

**Steps**:

1. Проверить repository root, активную ветку и `git status --short`; убедиться,
   что рабочая копия соответствует task head WP02 и не содержит чужих записей.
2. Получить `git rev-parse HEAD`, версию из authoritative packaging metadata и
   UTC timestamp начала/окончания сборки. Commit нельзя брать из сообщения,
   сохранённого в старом evidence.
3. Выбрать временный output directory вне tracked mission artifacts. Не
   добавлять wheel, build directory или dist cache в WP03 owned surface.
4. Запустить проектный wheel build тем способом, который поддерживает текущая
   конфигурация packaging; предпочтительно использовать изолированный build
   без публикации и сохранить точную команду в evidence.
5. Проверить, что команда не содержит upload/publish/release шага и что итогом
   является ровно ожидаемый wheel для текущей версии.
6. Для каждого созданного временного артефакта записать имя, размер и
   SHA-256; основной `artifact_sha256` вычислить по байтам готового wheel после
   завершения сборки.
7. Если build падает, записать точную стадию и безопасный текст ошибки в
   evidence со статусом `blocked`; не обходить проблему ручной подменой wheel.

**Files**: только
`kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json`;
wheel и build output находятся во временной директории и не коммитятся.

**Validation**: wheel существует, читается как ZIP, имеет ненулевой размер,
его SHA-256 повторно совпадает при независимом чтении, а source commit и
package version подтверждены командами из текущего checkout.

### Subtask T011: Выполнить zip-level inventory и hash checks

**Purpose**: проверить содержимое именно собранного wheel и зафиксировать
oracle для explicit-only distribution metadata.

**Steps**:

1. Открыть wheel через стандартный ZIP reader в read-only режиме и получить
   детерминированный отсортированный inventory с path, размером и CRC либо
   SHA-256 каждого relevant entry.
2. Проверить точное наличие
   `src/charter/offering/skills/spec-kitty-program-orchestrate/agents/openai.yaml`.
   Сходное имя, путь с другой раскладкой или файл из source tree вне архива не
   засчитываются.
3. Извлечь только байты exact metadata entry в память или временный файл и
   разобрать их YAML parser-ом, не исполняя содержимое и не импортируя skill.
4. Проверить, что `allow_implicit_invocation` существует на ожидаемом уровне и
   имеет именно boolean значение `false`, а не строку `"false"`, `0`, `null` или
   отсутствующее значение.
5. Записать entry size, entry SHA-256, разобранное policy value и статус
   проверки в evidence. Полное содержимое metadata можно не дублировать.
6. Проверить, что wheel inventory не содержит неожиданный второй canonical
   path, который мог бы скрывать конфликт package layout.
7. Повторить общий artifact SHA-256 после inventory и сравнить его с T010.
   Любое расхождение считать изменением артефакта и остановить delivery plan.
8. Выполнить предусмотренный distribution test или минимальный project-local
   oracle, если он уже существует; не писать новый тест в рамках WP03.
9. При неверном или отсутствующем metadata записать `failed` с причиной и
   mutation-oracle hint; не редактировать wheel вручную и не подменять статус.

**Files**: только `delivery-evidence.json`. Inventory может быть представлен
как отсортированный список relevant entries с digest; большие полные списки не
должны захламлять evidence без необходимости воспроизводимости.

**Validation**: независимая ZIP-проверка подтверждает exact path и YAML boolean
`false`; повторный hash совпадает; mutation check или существующий test oracle
доказывает, что отсутствие metadata либо неверная policy делают проверку красной.

### Subtask T012: Подготовить draft PR, пройти CI и self-review

**Purpose**: довести task-owned PR до состояния ready только после evidence и
зелёных обязательных проверок, оставив merge отдельным gate.

**Steps**:

1. Проверить diff task head и убедиться, что в нём только согласованные
   изменения WP02 и один WP03 evidence artifact; случайные файлы в PR не
   исправлять молча, а зафиксировать как blocker.
2. Сформировать draft PR с русским описанием наблюдаемого результата: ordinary
   startup, ownership-aware sync, exact distribution metadata и delivery gates.
3. В описании PR указать artifact version, source commit, SHA-256, команды
   T010/T011 и ссылку на `delivery-evidence.json`, не раскрывая секреты.
4. Дождаться завершения обязательного CI и сохранить имена checks, conclusion,
   commit SHA и время проверки. Pending check не считать зелёным.
5. Выполнить self-review diff и проверить соответствие spec.md, plan.md и
   requirement_refs WP03. Особое внимание уделить FR-005, FR-006, NFR-004,
   C-001 и C-002.
6. Проверить `git diff --check` и релевантные уже предусмотренные project gates;
   не расширять scope новым рефакторингом или исправлением соседних WP.
7. Перевести draft PR в ready только если required checks зелёные и self-review
   не нашёл блокирующих расхождений. Зафиксировать действие, actor и timestamp.
8. Не нажимать merge, не закрывать PR, не удалять ветку и не запускать release.
   Если ready невозможен из-за CI или доступа, записать `blocked` с точным
   внешним условием и оставить PR draft.

**Files**: сохраняется только evidence JSON; PR metadata и CI остаются во
внешней системе и цитируются идентификаторами, URL и commit SHA без копирования
приватных логов.

**Validation**: PR относится к ожидаемому task head, required checks имеют
зелёный conclusion либо evidence содержит честный blocker, self-review
зафиксирован, а merge/release не выполнялись.

### Subtask T013: Снять HOSTKEY snapshot и составить CAS-gated dry plan

**Purpose**: описать безопасную проверку будущей доставки на HOSTKEY по
наблюдаемому состоянию и immutable artifact identity без live mutation.

**Steps**:

1. Использовать только разрешённый read-only HOSTKEY snapshot helper или
   документированный read-only способ из текущего ops-профиля. Если helper или
   доступ недоступен, записать blocker; не заменять его догадкой.
2. Зафиксировать host/service identifier в минимальном объёме, timestamp,
   runtime/package version, ожидаемый skill root type и существующие path
   fingerprints. Не записывать auth headers, secrets или полный private payload.
3. Для каждого будущего CAS guard определить наблюдаемое поле и ожидаемое
   значение: artifact SHA-256, source commit/version, destination type,
   package-owned fingerprint и отсутствие неожиданного drift.
4. Разделить `observed_snapshot` и `proposed_dry_plan`: snapshot - только
   прочитанные факты, plan - условные шаги, которые допустимы лишь при полном
   совпадении guards.
5. Описать порядок будущего dry-run: повторно проверить artifact hash, затем
   текущий destination fingerprint, затем ownership-aware overlay. Добавить
   явный abort при mismatch, symlink/file collision, неизвестном drift или
   неполной проверке.
6. Для плана явно указать `apply: false`, `install: false`, `cleanup: false` и
   `scheduler: false`; отсутствие этих полей не считается защитой.
7. Исключить команды `pip install`, копирование в live skill root, удаление,
   restart и scheduler mutation из фактически выполненного snapshot.
8. Локально провалидировать, что JSON синтаксически корректен, CAS guards
   непусты, artifact SHA-256 совпадает с T010/T011, а статус плана не маскирует
   незавершённую или заблокированную проверку.

**Files**: только
`kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json`;
HOSTKEY остаётся неизменённым.

**Validation**: snapshot имеет timestamp и источник, содержит ожидаемое
состояние, dry plan содержит immutable artifact SHA и CAS guards, а read-only
журнал подтверждает отсутствие install, cleanup и scheduler действий.

## Контракт `delivery-evidence.json`

Создать валидный UTF-8 JSON с детерминированными ключами и без секретов. Минимум
должны присутствовать следующие поля:

- `schema_version`: версия схемы evidence, например `1`;
- `work_package_id`: `WP03`;
- `source_commit`: полный SHA текущего task head;
- `package_version`: версия, из которой собран wheel;
- `artifact`: имя, временный локальный источник, размер и `sha256`;
- `distribution_metadata`: exact path, entry hash, parsed policy и status;
- `subtasks`: записи T010, T011, T012 и T013 с командами, timestamp и status;
- `pr`: draft/ready state, PR identifier, head SHA, checks и merge status;
- `hostkey`: read-only snapshot, guards и dry plan, либо честный blocker;
- `scope_guard`: owned file, запреты C-001/C-002 и отсутствие live mutation.

Для каждой команды указывать `command`, `cwd`, `observed_at`, `status` и
краткий безопасный результат. Не копировать длинные логи, токены, cookies,
private host inventory или credential paths. Значения статуса должны отличать
`passed`, `blocked` и `failed`; `passed` нельзя использовать при пропущенной
проверке.

## Definition of Done

- [ ] Создан ровно `kitty-specs/global-skill-bootstrap-safety-01M20J6C/delivery-evidence.json`.
- [ ] T010 подтверждает wheel из текущего task head без публикации.
- [ ] Evidence содержит package version, полный source commit и SHA-256 wheel.
- [ ] T011 подтверждает exact metadata path и boolean `allow_implicit_invocation: false`.
- [ ] Zip inventory и hash checks воспроизводимы по сохранённым командам.
- [ ] T012 содержит draft PR, CI conclusions и self-review; ready выставлен
      только при зелёных обязательных checks или честно записан blocker.
- [ ] Merge, release и удаление ветки не выполнялись.
- [ ] T013 содержит timestamped HOSTKEY read-only snapshot и CAS-gated dry plan.
- [ ] План явно запрещает live install, cleanup и scheduler mutation.
- [ ] JSON проходит парсинг, не содержит секретов и соответствует owned scope.
- [ ] `git diff --check` и релевантные delivery checks либо пройдены, либо их
      blocker записан в evidence без замены фактов предположениями.

## Risks

- Сборка из неверного commit создаёт правдоподобный, но недействительный
  artifact. Мера: записать полный HEAD до build и сравнить его с PR head.
- Wheel может содержать stale или строковую policy metadata. Мера: exact ZIP
  path, YAML parser и строгая проверка Python boolean `False`.
- Локальный файл может измениться после hash. Мера: вычислить digest после
  закрытия файла и повторить его независимым чтением перед evidence.
- CI может быть pending или пересобрать другой commit. Мера: фиксировать head
  SHA и conclusion каждого required check.
- HOSTKEY snapshot может быть неполным или stale. Мера: timestamp, источник,
  explicit unknown fields и CAS abort при любом mismatch.
- Попытка «проверить» plan может превратиться в live mutation. Мера: dry plan
  должен иметь явные false-флаги и не содержать mutation commands.

## Reviewer Guidance

Проверяйте сначала, что evidence создан в единственном owned path и не
маскирует пропущенные проверки. Сопоставьте artifact SHA, package version и
source commit между T010, T011, PR head и T013.

Отдельно проверьте exact ZIP entry и тип boolean policy. Убедитесь, что PR
переведён в ready только после required CI, а merge/release отсутствуют.

Для HOSTKEY сопоставьте каждую proposed action с CAS guard и убедитесь, что
план останавливается при mismatch. Snapshot должен оставаться read-only:
отсутствие install, cleanup, scheduler и restart - обязательное условие.

Запустите:

```text
spec-kitty agent action implement WP03 --agent codex
```

Если любой gate не может быть проверен в текущей среде, отклоните вывод как
`blocked` с воспроизводимой причиной, а не как успешно завершённый delivery.
