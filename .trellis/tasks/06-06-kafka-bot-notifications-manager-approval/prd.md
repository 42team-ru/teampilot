# Kafka Bot Notifications And Manager Task Approval

## Problem

The backend already publishes bot-facing Kafka events and exposes task approval APIs, but the Telegram bot does not consume the current backend topics or provide a manager workflow for approving LLM-created tasks that are waiting in `PENDING_APPROVAL`.

## Goals

- Consume backend Kafka notifications from `bots.notifications`.
- Consume backend task confirmation events from `bots.tasks`.
- Show actionable deadline/stale notifications in Telegram.
- Add a manager-panel flow for reviewing and approving new tasks.
- Use the backend REST contract from Swagger:
  - `GET /tasks?chatId=...&localStatus=PENDING_APPROVAL`
  - `GET /tasks/{id}`
  - `POST /tasks/{id}/approve`
- Place the approval UX inside the existing team manager context, near team task actions.

## Non-Goals

- Do not redesign the whole task board/status model.
- Do not add manager-side rejection unless backend manager authorization supports it.
- Do not change backend Kafka producers unless strictly required by bot integration.

## UX Decision

The best fit is the existing private manager team panel:

`Главное меню -> Выбрать команду -> manager team context -> Новые задачи`.

This keeps approvals in a private manager workflow instead of noisy group-chat inline confirmations. The team context can also show a pending count on the button when available.

## Acceptance Criteria

- Bot subscribes to `bots.notifications` and formats `DEADLINE` / `STALE` events.
- Bot subscribes to `bots.tasks` and announces confirmed task creation in the team chat.
- Manager team panel exposes "Новые задачи" for linked teams.
- Pending task list fetches `PENDING_APPROVAL` via `localStatus`.
- Manager can approve a task with `POST /tasks/{id}/approve` authenticated by `X-Telegram-Id`.
- Existing old Kafka topics keep working where possible.
- Bot Python files compile successfully.
