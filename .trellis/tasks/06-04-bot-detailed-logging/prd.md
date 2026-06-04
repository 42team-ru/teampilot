# Bot detailed logging for team creation

## Goal

Improve diagnostics in the bot only. Team creation currently fails for users with
`Не удалось создать команду. Попробуй позже.` while logs only show a short warning
like `Unexpected status 403 on POST /admin/teams:`.

## Scope

- Change files only under `bot/`, plus Trellis task metadata.
- Add richer logs around bot service HTTP calls to the backend.
- Keep user-facing messages unchanged.
- Do not change backend behavior or API contracts.

## Requirements

- `bot/services/admin_service.py:create_team` must log enough context to diagnose
  `403` and other non-success statuses:
  - HTTP method and route
  - status code
  - request context such as telegram id, chat/team/task ids, params, and safe body
  - response body, even when empty
  - response headers useful for debugging
- Apply the same style to other bot service calls where practical, so HTTP
  failures are not silent or vague.
- Do not log secrets such as `X-Bot-Secret`, YouGile token, kanban API keys, MinIO
  secrets, or raw authorization headers.
- Preserve existing return values and fallback behavior.

## Verification

- Run bot package type/lint checks if available.
- At minimum compile Python files under `bot/`.
