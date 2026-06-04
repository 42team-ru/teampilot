# Task List Commands

## Goal

Allow Telegram users to ask the bot for their current tasks and allow team managers to see team task summaries.

## User Stories

- As a regular user, I can send `/mytasks` or ask "kakie u menya zadachi" and receive my active tasks.
- As a manager, I can send `/board` in a private chat or team group and receive a grouped team board summary.
- As a manager, I can send `/tasks @username` and receive tasks for a specific team member.
- I can press an "Obnovit" button to repeat the same request without typing the command again.

## Backend Requirements

- Provide a REST endpoint for task listing with filters needed by the bot.
- Required filter support:
  - assignee by Telegram user id.
  - active tasks.
  - team/group scope for board summaries.
- Existing Swagger is trusted as the current contract source and should remain compatible where possible:
  - `GET /tasks`
  - `GET /tasks/{id}`
  - `GET /tasks/yougile`
  - task statuses: `OPEN`, `IN_PROGRESS`, `REVIEW`, `BLOCKED`, `DONE`, `CANCELLED`.

## Bot Requirements

- `/mytasks`:
  - Calls Spring for tasks assigned to the sender with active statuses.
  - Responds within 2 seconds under normal backend latency.
  - Shows actual data on each request.
  - Shows each task title, deadline, optional priority if available in payload, and action buttons.
- `/board`:
  - Works in private chats and groups.
  - Available only to users with team role `MANAGER`.
  - Shows board date and grouped sections, at least active work, review, overdue.
- `/tasks @username`:
  - Available only to `MANAGER`.
  - Resolves the mentioned team member and shows that user's tasks.
- "Obnovit" button:
  - Repeats the original query context: my tasks, board, or target user tasks.

## Formatting

- Personal task list header: `Tvoi aktivnye zadachi`.
- Board header: `Doska komandy (<date>)`.
- Deadlines should be human-readable.
- Overdue deadlines should be explicitly marked.
- Empty states should be user-friendly.

## Acceptance Criteria

- `/mytasks` returns active assigned tasks using fresh backend data.
- `/board` is rejected for non-managers.
- `/board` works when called from a group.
- `/tasks @username` is rejected for non-managers.
- Refresh buttons repeat their original request.
- Backend and bot tests, lint, or available project checks pass.
