from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from loguru import logger

_MAX_LOG_VALUE_LENGTH = 2000
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "apikey",
    "access_key",
    "secret",
    "password",
    "token",
    "credential",
    "cookie",
)
_DEBUG_HEADER_NAMES = {
    "content-length",
    "content-type",
    "date",
    "location",
    "server",
    "www-authenticate",
    "x-amzn-requestid",
    "x-correlation-id",
    "x-request-id",
    "x-trace-id",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    if normalized.startswith("has_"):
        return False
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _trim(value: str) -> str:
    if len(value) <= _MAX_LOG_VALUE_LENGTH:
        return value
    return f"{value[:_MAX_LOG_VALUE_LENGTH]}...<truncated {len(value) - _MAX_LOG_VALUE_LENGTH} chars>"


def safe_log_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return "<redacted>"

    if isinstance(value, Mapping):
        return {str(k): safe_log_value(v, key=str(k)) for k, v in value.items()}

    if isinstance(value, list):
        return [safe_log_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(safe_log_value(item) for item in value)

    if isinstance(value, str):
        return _trim(value)

    return value


def safe_response_headers(headers: httpx.Headers) -> dict[str, str]:
    safe_headers: dict[str, str] = {}
    for name, value in headers.items():
        normalized = name.lower()
        if normalized in _DEBUG_HEADER_NAMES or normalized.startswith("x-"):
            safe_headers[name] = str(safe_log_value(value, key=name))
    return safe_headers


def response_body_for_log(response: httpx.Response) -> str:
    body = response.text
    if not body:
        return "<empty>"
    return _trim(body)


def log_http_request_error(
    *,
    service: str,
    method: str,
    path: str,
    error: Exception,
    context: Mapping[str, Any] | None = None,
    request_json: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
) -> None:
    logger.warning(
        "{} request failed: method={} path={} context={} params={} request_json={} "
        "error_type={} error={!r}",
        service,
        method,
        path,
        safe_log_value(context or {}),
        safe_log_value(params or {}),
        safe_log_value(request_json or {}),
        type(error).__name__,
        error,
    )


def log_http_response_error(
    response: httpx.Response,
    *,
    service: str,
    method: str,
    path: str,
    expected: str,
    context: Mapping[str, Any] | None = None,
    request_json: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
) -> None:
    logger.warning(
        "{} unexpected response: method={} path={} status={} reason={} expected={} "
        "context={} params={} request_json={} response_headers={} response_body={}",
        service,
        method,
        path,
        response.status_code,
        response.reason_phrase,
        expected,
        safe_log_value(context or {}),
        safe_log_value(params or {}),
        safe_log_value(request_json or {}),
        safe_response_headers(response.headers),
        response_body_for_log(response),
    )
