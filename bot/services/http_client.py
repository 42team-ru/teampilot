from __future__ import annotations

import asyncio
import json
import socket
import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import SimpleNamespace
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
        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds,
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
            sock_read=settings.HTTP_SOCK_READ_TIMEOUT_SECONDS,
        )
        self._trace_config = self._build_trace_config()
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
        phases: dict[str, float] = {}
        kwargs.setdefault("trace_request_ctx", {
            "request_id": request_id,
            "_request_started": started,
            "phases": phases,
        })
        logger.info(
            "HTTP request starting: request_id={} method={} url={} params={}",
            request_id,
            method,
            url,
            _safe_params(kwargs.get("params")),
        )
        try:
            async with self._get_session().request(method, url, **kwargs) as response:
                body_started = time.perf_counter()
                text = await response.text(errors="replace")
                phases["body_read_ms"] = _elapsed_ms(body_started)
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "HTTP response received: request_id={} method={} url={} status={} elapsed_ms={:.1f} phases={}",
                    request_id,
                    method,
                    url,
                    response.status,
                    elapsed_ms,
                    _slow_phases(phases),
                )
                if elapsed_ms >= settings.HTTP_SLOW_REQUEST_MS:
                    logger.warning(
                        "Slow HTTP request: request_id={} method={} url={} status={} elapsed_ms={:.1f} phases={}",
                        request_id,
                        method,
                        url,
                        response.status,
                        elapsed_ms,
                        phases,
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
                "HTTP request failed: request_id={} method={} url={} elapsed_ms={:.1f} phases={} error_type={} error={!r}",
                request_id,
                method,
                url,
                elapsed_ms,
                phases,
                type(error).__name__,
                error,
            )
            raise HttpRequestError(error) from error

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            family = socket.AF_INET if settings.HTTP_FORCE_IPV4 else 0
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    ttl_dns_cache=300,
                    family=family,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True,
                ),
                timeout=self._timeout,
                trace_configs=[self._trace_config],
                trust_env=False,
            )
        return self._session

    def _build_trace_config(self) -> aiohttp.TraceConfig:
        trace = aiohttp.TraceConfig()

        async def queued_start(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_start(ctx, "queued")

        async def queued_end(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_end(ctx, "queued_ms")

        async def dns_start(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_start(ctx, "dns")

        async def dns_end(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_end(ctx, "dns_ms")

        async def connect_start(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_start(ctx, "connect")

        async def connect_end(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _set_phase_end(ctx, "connect_ms")

        async def headers_sent(_session: aiohttp.ClientSession, ctx: SimpleNamespace, _params: Any) -> None:
            _phase_data(ctx)["headers_sent_ms"] = _elapsed_ms(_request_started(ctx))

        trace.on_connection_queued_start.append(queued_start)
        trace.on_connection_queued_end.append(queued_end)
        trace.on_dns_resolvehost_start.append(dns_start)
        trace.on_dns_resolvehost_end.append(dns_end)
        trace.on_connection_create_start.append(connect_start)
        trace.on_connection_create_end.append(connect_end)
        trace.on_request_headers_sent.append(headers_sent)
        return trace


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


def _phase_data(ctx: SimpleNamespace) -> dict[str, float]:
    trace_ctx = getattr(ctx, "trace_request_ctx", None)
    if not isinstance(trace_ctx, dict):
        return {}
    phases = trace_ctx.get("phases")
    if not isinstance(phases, dict):
        phases = {}
        trace_ctx["phases"] = phases
    return phases


def _request_started(ctx: SimpleNamespace) -> float:
    trace_ctx = getattr(ctx, "trace_request_ctx", None)
    if isinstance(trace_ctx, dict):
        started = trace_ctx.get("_request_started")
        if isinstance(started, float):
            return started
        started = time.perf_counter()
        trace_ctx["_request_started"] = started
        return started
    return time.perf_counter()


def _set_phase_start(ctx: SimpleNamespace, name: str) -> None:
    trace_ctx = getattr(ctx, "trace_request_ctx", None)
    if isinstance(trace_ctx, dict):
        trace_ctx[f"_{name}_started"] = time.perf_counter()


def _set_phase_end(ctx: SimpleNamespace, key: str) -> None:
    trace_ctx = getattr(ctx, "trace_request_ctx", None)
    if not isinstance(trace_ctx, dict):
        return
    started = trace_ctx.get(f"_{key.removesuffix('_ms')}_started")
    if isinstance(started, float):
        _phase_data(ctx)[key] = _elapsed_ms(started)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def _slow_phases(phases: dict[str, float]) -> dict[str, float]:
    threshold = settings.HTTP_TRACE_PHASE_MS
    return {
        key: value
        for key, value in phases.items()
        if value >= threshold
    }


http_client = HttpClient(settings.HTTP_TIMEOUT_SECONDS)
