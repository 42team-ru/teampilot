# Fix Telegram HTML parse error in meeting start

## Goal

Fix the Telegram bot crash when a manager opens the meeting creation flow from a team context menu.

## What I already know

* Telegram rejects the `edit_text` call with `Bad Request: can't parse entities`.
* The traceback points to `bot/handlers/manager.py` in `team_ctx_meeting_start`.
* The message text contains an invalid HTML bold tag: `<b>Созвон/b>` instead of `<b>Созвон</b>`.
* The bot uses `DefaultBotProperties(parse_mode=ParseMode.HTML)`, so malformed HTML breaks message sending/editing.

## Assumptions

* The desired behavior is to keep HTML formatting enabled and fix the malformed tag.
* This task should not redesign message formatting or change parse mode globally.

## Requirements

* Correct the malformed HTML tag in the meeting start prompt.
* Check for the same malformed closing-tag pattern in the bot code.
* Verify the Python bot code still parses/compiles.

## Acceptance Criteria

* [x] `team_ctx_meeting_start` sends/edits a valid HTML message.
* [x] No matching malformed `.../b>` tag remains in `bot/handlers`.
* [x] Basic Python syntax check passes for the touched bot module.

## Definition of Done

* Code is updated.
* Targeted verification is run.
* Any residual risk is reported.

## Out of Scope

* Adding a centralized safe HTML rendering helper.
* Auditing every Telegram message for unescaped user-controlled text.
* Changing the bot-wide parse mode.

## Technical Notes

* User supplied traceback from aiogram `TelegramBadRequest`.
* Main impacted file: `bot/handlers/manager.py`.
