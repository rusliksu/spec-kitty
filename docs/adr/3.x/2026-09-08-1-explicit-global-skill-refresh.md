---
title: Явное ownership-aware обновление user-global skills
description: Обычный запуск CLI не пишет в user-global skill roots; явные install, upgrade и repair обновляют только package-owned paths.
status: Accepted
date: '2026-09-08'
---

## Контекст

Spec Kitty хранит canonical skills в user-global roots, включая `~/.agents/skills/`. До этого решения `main_callback()` запускал `ensure_global_agent_skills()` при каждой обычной команде. При несовпадении version marker синхронизация удаляла весь существующий каталог canonical skill и копировала packaged tree заново.

Whole-directory replacement считал package-owned весь каталог целиком. Поэтому пользовательский `agents/openai.yaml`, заметка или другой путь, отсутствующий в текущем дистрибутиве, удалялся при обычном запуске CLI. Такой startup не имеет достаточного ownership для этой записи.

## Решение

Обычные команды больше не вызывают global skill refresh. User-global skills остаются machine-level surface, но запись в них выполняют только явные `init`, `upgrade` и `repair` flows.

Явное обновление выполняет overlay от `CanonicalSkill.skill_dir`:

- каждый path, присутствующий в packaged source tree, считается package-owned и обновляется;
- exact collision заменяется в пользу source, включая read-only destination;
- если exact collision является symlink, удаляется сам link, без перехода к его target;
- после успешной записи write bits снимаются только с записанных package-owned files;
- paths, отсутствующие в source tree, сохраняются вместе с bytes и mode;
- соседние canonical skills не затрагиваются.

Очистка retired skills остаётся отдельной exact-name политикой на основании `RETIRED_CANONICAL_SKILL_NAMES`. Она не расширяется до эвристического удаления неизвестных каталогов.

`runtime.agent_skills` сохраняет lock, version marker и orchestration явного refresh, но делегирует overlay единому installer seam. Вторая destructive copy/delete implementation удаляется.

## Границы

User-global slash commands регулируются отдельным принятым решением. Их startup refresh и `ensure_global_agent_commands()` этим ADR не меняются.

Решение не устанавливает новый package в live roots, не выполняет HOSTKEY mutation и не публикует release. Такие действия требуют отдельных delivery gates.

## Последствия

Пользовательские metadata и другие unknown paths внутри canonical skill roots больше не теряются при обычной команде и сохраняются при явном refresh. Package-owned files продолжают получать актуальное содержимое дистрибутива и read-only mode.

Пользователь, которому нужно обновить skills после установки новой версии, запускает явный `init`, `upgrade` или `repair` flow. Version marker больше не превращает обычную команду в скрытого владельца записи в global skill roots.

## Связанные решения

- [Global Skill Installation with Per-Project Symlinks](2026-04-08-3-global-skill-installation-per-project-symlinks.md) сохраняет решение о global canonical install; его symlink projection уже superseded отдельным copy-delivery ADR.
- [Global Slash Command Installation](2026-04-07-1-global-slash-command-installation.md) остаётся без изменений.
