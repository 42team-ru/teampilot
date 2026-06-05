# Backend Contract Notes

## REST

Swagger and backend code agree on task approval:

- `GET /tasks` accepts `chatId`, `assignee`, `localStatus`, pageable params.
- `TaskResponse.localStatus` values are `PENDING_APPROVAL`, `ACTIVE`, `DELETED_FROM_YOUGILE`.
- `POST /tasks/{id}/approve` is authenticated and checks that the current user is a manager of the task team.
- `POST /tasks/{id}/cancel` is restricted to bot/system admin, so it should not be exposed as a manager rejection action from the bot.

## Kafka

Backend topic constants:

- `bots.notifications` carries `BotNotificationEvent`.
- `bots.tasks` carries `TaskConfirmationEvent`.

`BotNotificationEvent` fields:

- `telegramId`
- `chatId`
- `type`: `DEADLINE` or `STALE`
- `taskId`
- `taskTitle`

`TaskConfirmationEvent` fields:

- `taskId`
- `chatId`
- `title`
- `description`
- `assigneeUsername`
- `deadline`
- `autoConfirmed`

Spring's JSON serializer is expected to emit camelCase JSON. Bot models should accept both camelCase and snake_case to be tolerant of older producers.
