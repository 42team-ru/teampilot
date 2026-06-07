# Fix Missing Bot Reminders Handler Import

## Goal

Make `uv run python main.py` start past module imports by removing the stale dependency on `handlers.reminders`, which is not present in the bot package.

## Requirements

* `bot/main.py` must not import or include a router from a missing `handlers.reminders` module.
* Existing notification delivery through Kafka topic `bots.notifications` must remain unchanged.
* The bot package should be importable after the change.

## Acceptance Criteria

* [x] Running a bot import check does not raise `ModuleNotFoundError: No module named 'handlers.reminders'`.
* [x] No unrelated bot routers are removed.
* [x] Existing tests still pass or any inability to run them is documented.

## Definition of Done

* Focused code change is implemented.
* Relevant bot verification command is run.
* Trellis quality check is performed.

## Technical Approach

Remove the stale `reminders_router` import and `dp.include_router(reminders_router)` call from `bot/main.py`. Deadline and stale notifications are already consumed from Kafka in `bot/kafka/consumer.py`, so no replacement Telegram handler module is needed for this crash.

## Out of Scope

* Adding new reminder commands or changing reminder message text.
* Changing backend scheduler or Kafka notification contracts.

## Technical Notes

* User reported: `ModuleNotFoundError: No module named 'handlers.reminders'` from `bot/main.py`.
* `rg --files bot` shows no `bot/handlers/reminders.py`.
* `git log --all -- bot/handlers/reminders.py` shows no historical file.
* `bot/kafka/consumer.py` already handles `TOPIC_BOTS_NOTIFICATIONS` and formats `BotNotificationEvent` types including `DEADLINE` and `STALE`.
