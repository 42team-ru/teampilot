# Bot Nested Menu Panels

## Problem

The bot currently uses decorative inline buttons such as `━━ Работа ━━`, `━━ Задачи ━━`, and `━━ Управление командой ━━` as visual separators. They answer with `noop`, so users see them as broken or non-clickable buttons.

## Goals

- Remove decorative non-action section buttons from bot panels.
- Turn high-level sections into real clickable menus.
- Keep manager and member panels navigable by buttons only.
- Split team context actions into separate panels:
  - tasks
  - files
  - team management
- Keep existing backend API calls and task action callback contracts unchanged.

## Acceptance Criteria

- No bot keyboard uses the `━━ ... ━━` section button pattern.
- Main user panel has clickable block buttons instead of decorative section rows.
- Manager team panel opens nested panels for tasks, files, and team management.
- Member team panel opens nested panels for tasks and files.
- Existing direct actions remain reachable from nested panels.
- Python files compile successfully.
