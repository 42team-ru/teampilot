# Error Handling

> How errors are handled in this project.

---

## Overview

<!--
Document your project's error handling conventions here.

Questions to answer:
- What error types do you define?
- How are errors propagated?
- How are errors logged?
- How are errors returned to clients?
-->

(To be filled by the team)

---

## Error Types

<!-- Custom error classes/types -->

(To be filled by the team)

---

## Error Handling Patterns

<!-- Try-catch patterns, error propagation -->

(To be filled by the team)

---

## API Error Responses

<!-- Standard error response format -->

### Scenario: External Auth Credential Failures

#### 1. Scope / Trigger
- Trigger: backend endpoints that validate user-entered credentials against an external service, such as YouGile login/password during Telegram bot setup.
- These failures are user-correctable input problems, not backend outages.

#### 2. Signatures
- Backend endpoint: `POST /auth/yougile/auth`
- Service boundary: `AuthService.yougileAuth(...)` calls YouGile company/API-key endpoints with user credentials.

#### 3. Contracts
- Request fields include `chatId`, `login`, `password`, and optional `companyId`.
- Expected credential rejection response:
  - HTTP status: `401 Unauthorized`
  - `ErrorResponse.detail`: safe Russian user-facing text, e.g. `Не удалось войти в YouGile: проверьте логин и пароль.`
- The response must not expose upstream URLs, raw exception strings, passwords, API keys, tokens, or stack traces.

#### 4. Validation & Error Matrix
- External service returns `401 Unauthorized` for credential-based auth -> throw `AppException.unauthorized(...)`.
- External service returns another non-success status during auth -> keep it as an internal/external-service failure unless the status is known to be user-correctable.
- Backend cannot reach external service or times out -> surface as backend/external-service unavailable.
- Local validation fails before external call -> use the normal validation/bad-request path.

#### 5. Good/Base/Bad Cases
- Good: wrong YouGile password returns backend `401` with safe detail; the bot asks the user to re-enter credentials.
- Base: valid credentials return company or board selection data as before.
- Bad: wrong YouGile password becomes backend `500` with text like `401 Unauthorized from POST https://...`.

#### 6. Tests Required
- Backend unit or slice test: upstream `WebClientResponseException` with status `401` maps to `AppException` status `401`.
- Bot handler/helper test: backend `401` with YouGile detail and legacy wrapped `500` with upstream `401 Unauthorized` both render the setup retry path.
- If tests are explicitly skipped for a specific change, document the reason and run compile/syntax checks.

#### 7. Wrong vs Correct

#### Wrong
```java
catch (Exception e) {
    throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
}
```

#### Correct
```java
catch (WebClientResponseException e) {
    if (e.getStatusCode().value() == 401) {
        throw AppException.unauthorized("Не удалось войти в YouGile: проверьте логин и пароль.");
    }
    throw AppException.internalError("YouGile API unavailable");
}
```

---

## Common Mistakes

<!-- Error handling mistakes your team has made -->

(To be filled by the team)
