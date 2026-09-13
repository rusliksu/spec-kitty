# Результаты по связанным issues

| issue | verdict | evidence_ref | title | scope | repo |
|---|---|---|---|---|---|
| #26 | fixed | https://github.com/rusliksu/spec-kitty/actions/runs/34750989826; traces/owned-checkout-seam-evidence.md | Команды задач и статусов видят объявленную рабочую копию | Реализация f2dc787c6, неизменность primary, совместимость без флага; приёмка всей миссии записывается отдельно | rusliksu/spec-kitty |
| #3328 | verified-already-fixed | https://github.com/spec-kitty/spec-kitty/issues/3328; src/mission_runtime/resolution.py; tests/next/test_decision_unit.py; tests/next/test_runtime_bridge_unit.py; https://github.com/rusliksu/spec-kitty/actions/runs/34750989826 | Существующая граница явного владения для создания и продвижения миссии | Цитируемая в research.md D-8 существующая поддержка effective_root уже находится в исходной базе; текущая работа использует её для команд задач и статусов | spec-kitty/spec-kitty |

Строка upstream описывает существующий контракт, процитированный в исследовании.
Issue проверен через GitHub и закрыт; его реализация и тесты уже присутствовали
до данного исправления. Эта миссия не заявляет новую проверку SaaS или релиза upstream.
Кандидат для результатов тестов: f2dc787c6f02329df84bf3707edd742a4edccd18.
Полный дополнительный CI и окончательная приёмка на момент составления ещё ожидаются.
