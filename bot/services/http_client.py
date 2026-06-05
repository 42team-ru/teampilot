from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import aiohttp
from loguru import logger

from config import settings


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    reason_phrase: str
    headers: Mapping[str, str]
    text: str

    def json(self) -> Any:
        return json.loads(self.text)


class HttpRequestError(Exception):
    def __init__(self, error: Exception) -> None:
        self.original_error = error
        super().__init__(f"{type(error).__name__}: {error}")


class HttpClient:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("POST", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("DELETE", url, **kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        request_id = uuid4().hex[:12]
        started = time.perf_counter()
        logger.info(
            "HTTP request sent: request_id={} method={} url={} params={}",
            request_id,
            method,
            url,
            _safe_params(kwargs.get("params")),
        )
        try:
            async with self._get_session().request(method, url, **kwargs) as response:
                text = await response.text(errors="replace")
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "HTTP response received: request_id={} method={} url={} status={} elapsed_ms={:.1f}",
                    request_id,
                    method,
                    url,
                    response.status,
                    elapsed_ms,
                )
                if elapsed_ms >= settings.HTTP_SLOW_REQUEST_MS:
                    logger.warning(
                        "Slow HTTP request: request_id={} method={} url={} status={} elapsed_ms={:.1f}",
                        request_id,
                        method,
                        url,
                        response.status,
                        elapsed_ms,
                    )
                return HttpResponse(
                    status_code=response.status,
                    reason_phrase=response.reason or "",
                    headers=dict(response.headers),
                    text=text,
                )
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.warning(
                "HTTP request failed: request_id={} method={} url={} elapsed_ms={:.1f} error_type={} error={!r}",
                request_id,
                method,
                url,
                elapsed_ms,
                type(error).__name__,
                error,
            )
            raise HttpRequestError(error) from error

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ttl_dns_cache=300),
                timeout=self._timeout,
                trust_env=False,
            )
        return self._session


def _safe_params(params: Any) -> Any:
    if not isinstance(params, Mapping):
        return params or {}

    return {
        str(key): "<redacted>" if _is_sensitive_key(str(key)) else value
        for key, value in params.items()
    }


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    return any(
        part in normalized
        for part in (
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
    )


http_client = HttpClient(settings.HTTP_TIMEOUT_SECONDS)
