# AdminController: создание команды

## Goal

Реализовать один эндпоинт `POST /admin/teams` — создаёт Team и привязывает первого пользователя-ADMIN.
Из комментария в файле: «Создает команду с названием, userId/telegramId/telegramUsername. Помимо этой ручки не нужно ничего делать».

## Requirements

- `POST /admin/teams` принимает: `chatTitle`, `teamId`, `kanbanId`, `kanbanApiKey`, `adminTelegramId`, `adminUsername`
- Ищет User по `adminTelegramId`; если нет — создаёт с ролью `SYSTEM_ADMIN`
- Создаёт `Team` (или upsert по `teamId`)
- Создаёт `TeamUser` с ролью `TeamRole.ADMIN`, привязывая user к team
- Возвращает `TeamResponse` (201 Created)
- Нет `/api` префикса в маппинге (по CLAUDE.md)

## Technical Approach

- Новый `dto/request/AdminCreateTeamRequest.java`
- Новый `repository/TeamUserRepository.java`
- Новый метод `TeamService.createWithAdmin(AdminCreateTeamRequest)` — вся логика там
- `AdminController` вызывает сервис, возвращает `ResponseUtils.created`

## Acceptance Criteria

- [ ] `POST /admin/teams` создаёт Team + TeamUser в БД
- [ ] Если пользователь уже есть — не дублируется
- [ ] Компилируется
