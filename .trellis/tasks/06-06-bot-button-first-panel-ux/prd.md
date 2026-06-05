# Bot Button-First Panel UX

## Problem

After `/start`, users still need to know command names such as `/mytasks`, `/tasks`, `/board`, and `/upload` for common flows. Manager and member panels also show actions as a flat list, which makes the bot feel less like a panel.

## Goals

- Make core bot flows reachable from buttons after `/start`.
- Use wider two-button rows where actions are peers.
- Group manager team actions into clear blocks:
  - task/board actions
  - files
  - team management
- Group member team actions into clear blocks:
  - task actions
  - files
- Keep existing callback handlers and command handlers working.
- Avoid changing backend contracts.

## Non-Goals

- Do not replace all inline keyboards with reply keyboards.
- Do not remove command handlers; keep them as shortcuts/backward compatibility.
- Do not redesign registration/setup flows beyond navigational buttons.

## Acceptance Criteria

- Main menu includes button access to personal tasks, team selection, and help.
- Manager team panel shows task/board/file actions separately from management actions.
- Member team panel shows task/file actions without requiring `/tasks` or `/upload`.
- Manager board view is reachable from a button.
- Help text no longer instructs users to memorize commands as the primary path.
- Changed Python files compile successfully.
