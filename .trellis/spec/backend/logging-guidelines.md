# Logging Guidelines

> How logging is done in this project.

---

## Overview

The Python bot uses `loguru` for application logs.

Bot HTTP clients log failed external calls through `bot/services/http_logging.py`.
Use the shared helper for non-success responses and `httpx.RequestError`
exceptions so logs include the method, route, status code, expected status,
safe request context, safe params/body, selected response headers, and response
body.

---

## Log Levels

<!-- When to use each level: debug, info, warn, error -->

- `warning`: external service failures that are handled by fallback return
  values or user-facing retry messages.
- `error`: unexpected failures that cannot be handled locally or break message
  processing.

---

## Structured Logging

<!-- Log format, required fields -->

Prefer `loguru` parameterized messages over f-strings for diagnostic payloads:

```python
logger.warning(
    "Backend unexpected response: method={} path={} status={} context={}",
    method,
    path,
    response.status_code,
    context,
)
```

For bot HTTP calls, prefer `log_http_request_error(...)` and
`log_http_response_error(...)` instead of hand-written one-line status logs.

---

## What to Log

<!-- Important events to log -->

- External service request failures and non-success responses.
- HTTP method, route, status code, reason phrase, expected status, request
  context, params/body after redaction, selected response headers, and response
  body.
- Empty response bodies explicitly as `<empty>` so failures like `403` without a
  body are visible.

---

## What NOT to Log

<!-- Sensitive data, PII, secrets -->

- Do not log `X-Bot-Secret`, `Authorization`, tokens, passwords, API keys,
  MinIO access/secret keys, YouGile tokens, or raw cookies.
- Use `safe_log_value(...)` or the shared HTTP logging helpers when logging
  request payloads that may contain secrets such as `kanbanApiKey`.
