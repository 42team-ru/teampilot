# Обработать ошибку авторизации YouGile в боте

## Goal

When a manager connects YouGile through the Telegram bot and YouGile rejects the credentials, the bot should show a clear retry prompt instead of a raw backend 500 message with upstream API details.

## Requirements

* For `POST /auth/yougile/auth`, invalid YouGile credentials must be treated as a user-correctable authentication problem, not as an internal backend failure.
* The Telegram setup flow must catch YouGile auth backend errors locally and keep the user in the setup FSM so they can retry.
* The message shown to the user must be in Russian and must not expose upstream URLs, exception text, stack traces, or backend trace IDs for the expected credential failure.
* The existing successful path remains unchanged: company selection, board selection, and final setup still work as before.
* Unexpected backend/network failures may still use the generic backend error path.

## Acceptance Criteria

* [ ] A 401 from YouGile while listing companies no longer surfaces to the bot as backend 500.
* [ ] In the setup password step, invalid credentials produce a friendly message like "Не удалось войти в YouGile. Проверь логин и пароль..." and allow retry without `/cancel`.
* [ ] The retry path asks for login again or otherwise makes the next expected input clear.
* [ ] Password messages are still deleted when possible.
* [ ] Compile/syntax checks relevant to changed Python and Java code pass, or any inability to run them is documented.

## Definition of Done

* No new tests for this change per user request.
* Existing code style and error handling conventions are preserved.
* No unrelated dirty files are modified.

## Technical Approach

* In backend `AuthService`, map upstream YouGile `401 Unauthorized` from credential-based auth calls to `AppException.unauthorized(...)` with a safe, user-facing detail.
* Keep unexpected YouGile failures as internal errors.
* In bot `setup.py`, catch `BackendApiError` around `yougile_auth(...)` in the password and company-selection steps, show setup-specific retry text for 401, and re-enter the login/password flow as appropriate.

## Decision (ADR-lite)

**Context**: The current generic middleware is correct for unexpected backend failures, but it produces a poor UX for an expected credential error during YouGile setup.

**Decision**: Fix the status mapping at the backend boundary and add local bot handling in the setup flow.

**Consequences**: The API becomes semantically cleaner for other clients, and the bot can present a concise retry message without leaking upstream details. Other unexpected failures still retain generic diagnostics.

## Out of Scope

* Redesigning the whole YouGile setup wizard.
* Adding a retry counter or account-lock behavior.
* Changing unrelated YouGile sync/task creation error handling.

## Technical Notes

* Relevant bot files inspected:
  * `bot/handlers/setup.py`
  * `bot/handlers/manager.py`
  * `bot/services/team_service.py`
  * `bot/services/backend_error.py`
  * `bot/main.py`
* Relevant backend files inspected:
  * `backend/monolith/src/main/java/ru/team42/monolith/service/AuthService.java`
  * `backend/core/web-common/src/main/java/ru/team42/backend/web_common/exception/AppException.java`
  * `backend/core/web-common/src/main/java/ru/team42/backend/web_common/exception/GlobalExceptionHandler.java`
* Existing unrecognized dirty file before this task:
  * `backend/monolith/src/main/java/ru/team42/monolith/config/DataSeeder.java`
