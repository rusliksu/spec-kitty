# Проверка команд в выбранной рабочей копии

## Проверяемый результат

Команды перехода, ревью, финализации и чтения используют явно выбранный checkout.
Полный сценарий `in_progress → for_review → in_review → approved` проверен на
зарегистрированных Git worktree как при отсутствии миссии в основной копии,
так и при наличии другой копии той же миссии. Проверяются реальные события,
снимок, сохранённый в Git документ ревью и неизменность основной копии.

## Исходные дефекты и исправления

Исходная версия дополнительной приёмки — `b0f58f49b28f4b51cdf2f51b40ad7aa97c78c182`.
До исправлений получены следующие воспроизводимые отказы:

| Сценарий | Исходный результат | Доказательство после исправления |
|---|---|---|
| Структурированное одобрение | 2 failed: каталог подзадач искался в другой копии | Проверяется записанный `review_result`; неверный payload не меняет файлы |
| `status validate` и `status lifecycle` | 2 failed: отсутствовала опция checkout | Чтение выбранной миссии, отказы для чужого пути и без объявления |
| `finalize-tasks` | 3 failed: ноль найденных задач или попытка коммита в primary | 4 сценария: dry-run/запись, миссия только в owned/в обеих копиях |
| Полный цикл ревью при двух копиях | Старый статус читался из primary перед решением и повторно перед записью | Полный цикл проходит; HEAD, индекс и файлы primary неизменны |
| Предупреждение о расхождении | 2 failed: предупреждение отсутствовало | Диагностика в stderr, корректный JSON в stdout |
| Незавершённая подзадача | Проверка отказывает даже при переданном флаге завершённости | Событие ревью не записывается |
| Исходные результаты тестов | Независимое ревью обнаружило чтение primary baseline | В двух копиях разные результаты; gate получает owned baseline |

## Локальные проверки

13 сентября 2026 года:

- `out/owned-candidate-tests.xml`: **188 passed**. В набор входят четыре файла
  сценариев owned checkout, проверки workspace, финализации и разбора задач,
  чтения baseline и две архитектурные проверки разрешения mission surface.
- `out/review-default-regressions.xml`: **121 passed, 6 failed**.
  Все шесть отказов в `tests/review/test_cycle.py` повторены на исходном коммите
  в отдельном клоне: `out/baseline-cycle-failures.xml`. Причины связаны с Windows
  и сохранением переводов строк/индекса; исключения и пропуски не добавлялись.
- Ruff на всех изменённых Python-файлах: **passed**.
- Два изолированных отрицательных контроля: **2 ожидаемых failed**
  (`out/owned-mutation-controls.xml`). Подмена основы U на HEAD обнаружена сравнением
  с реальным upstream SHA; замена корректного автора входного вердикта обнаружена
  сравнением с фактически записанным `review_result`. Исходный код файлов не менялся.
- Mypy `--strict` на изменённых модулях: **9 сообщений**, те же девять получены
  на исходном коммите; новых сообщений нет. Полный strict-check не объявляется зелёным.
- `finalize-tasks --validate-only --owned-checkout <task-checkout> --json`:
  `validation_passed`, две задачи, обе уже инициализированы, новых событий и изменений нет.
- `accept --diagnose` кодом отдельного PR #28 правильно видит исходную миссию и
  обе задачи. На момент этого снимка они ещё в работе; приёмка не объявлена успешной.

Локальные XML и диагностические отчёты находятся в игнорируемом каталоге `out/`
рабочей копии. Повторяемая команда основного набора:

```powershell
$env:PYTHONPATH=(Get-Location).Path+'/src'
python -m pytest tests/tasks/test_single_branch_owned_review.py tests/status/test_status_owned_checkout_seam.py tests/tasks/test_finalize_owned_checkout_seam.py tests/tasks/test_move_task_owned_checkout_seam.py tests/runtime/test_workspace_context_unit.py tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py tests/specify_cli/cli/commands/agent/test_tasks_finalize_validation.py tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_baseline_read.py tests/architectural/test_no_read_side_bypass.py tests/architectural/test_single_mission_surface_resolver.py -q
```

## Неизменность основной копии

До и после проверок основной checkout `C:/Users/Ruslan/spec-kitty` остаётся чистым,
HEAD — `78c1e9ab1f6d110398e449c2cc156d981dbc68c4`.
Git blob замороженного `kitty-ops/lifecycle.jsonl` —
`b0c8620e5b611c7ff53f6014a31a27328d7c7509`; байты сохранены.
В сценариях проверяются также первичные файлы и индекс Git, включая копию миссии,
которая намеренно отличается от выбранной.

## Внешняя проверка и приёмка

Работа публикуется в [PR #27](https://github.com/rusliksu/spec-kitty/pull/27).
Ранее зелёные прогоны этой ветки не заменяют проверку новых исправлений.
Для новой версии требуется полный запуск `ci-quality.yml` с `run_all=true`,
в том числе фактическое исполнение sync-тестов, и обычная проверка покрытия PR.
Результат полного CI, его точный SHA и окончательный результат приёмки будут
дописаны после завершения проверок. Сейчас эти пункты остаются незавершёнными.

Первый прогон новой реализации: [CI 34748862869](https://github.com/rusliksu/spec-kitty/actions/runs/34748862869),
SHA `44e07eb6fe3c6c618d6ddc5fac7c37ac6381240c`. Шард архитектурных проверок 1
отклонил assertion, который проверял только число документов ревью. Он усилен
проверкой конкретного имени; повторная локальная проверка архитектурного ограничения
и single_branch-сценариев прошла: **24 passed**. Остальные задания этого CI ещё выполняются.

Ручной полный запуск с `run_all=true` четыре раза вернул HTTP 500 и не создал run.
Workflow на default branch и кандидате совпадает с ранее успешно запускавшимся
YAML; Actions разрешены. Причина ошибки не установлена. Sync-задания обычного
PR пропущены фильтром, поэтому их прохождение не заявляется.

Для самой миссии штатно выполнен переход первой задачи в `for_review`, событие
`01M2D097DWVVE3PP7734H4XXQY`. Исполнитель, assignee и PID записаны новым событием.
Широкая локальная pre-review проверка сообщила `unverified_baseline` и
`<gate-coverage-junit>`; это **не зелёный результат тестов**. Переход разрешён
существующим advisory-режимом (`block_enabled=false`, `force_bypassed=false`),
никакие `force` или `skip` не применялись. `status validate` после перехода прошёл
без ошибок и предупреждений. Обе задачи ещё не имеют окончательного одобрения.

PR #27 и [PR #28](https://github.com/rusliksu/spec-kitty/pull/28) не сливаются.
Релиз, установка глобального runtime и развёртывание в этот пакет не входят.
