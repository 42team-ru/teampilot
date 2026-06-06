# Route Task Notifications To Direct Messages

## Goal

Task notifications must be delivered through direct messages with the bot, not posted into team group chats.

## Requirements

- Managers receive direct-message notifications for all task changes in their teams.
- If a task is assigned to a specific user, that assignee also receives a direct-message notification.
- If a task has no assignee, all team members receive the direct-message notification.
- Group chats must not receive these task notifications.
- Delivery failures to individual DMs should be logged and must not fall back to the group chat.

## Scope

- Applies to bot task notifications currently sent from Spring to Telegram via Kafka, especially `tasks.state` and `bots.tasks`.
- Existing non-task setup/auth command replies are out of scope.

## Acceptance Criteria

- Task state events carry recipient Telegram IDs instead of relying on group chat delivery.
- Bot sends task state and task confirmation messages to direct-message recipients only.
- No fallback to group chat remains for task notification delivery.
- Existing Kafka camelCase/Pydantic alias contract stays valid.
