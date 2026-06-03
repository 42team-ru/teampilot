# Seed Admin Telegram Users

## Requirements

- Update `ru.team42.monolith.config.DataSeeder` to seed the following Telegram users:
  - Telegram ID `2031863132`, username `eiiwoqodhkqoqo`, last name `Мельник`, first name `владмиир`
  - Telegram ID `713978344`, username `idzey878`, last name `Пантюхин`, first name `Кирилл`
- Both users must receive `SystemRole.SYSTEM_ADMIN`, including when a user with the Telegram ID already exists.
- Preserve idempotency by not creating duplicates when a user with the Telegram ID already exists.

## Acceptance Criteria

- `DataSeeder` creates both specified users as system admins on startup when missing.
- Existing users with those Telegram IDs are updated to the specified Telegram profile data and `SYSTEM_ADMIN`.
- Backend compilation for the monolith module passes.
