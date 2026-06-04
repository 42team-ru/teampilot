from __future__ import annotations

from dataclasses import dataclass
from html import escape

from services.http_client import HttpResponse


@dataclass(frozen=True)
class BackendApiError(Exception):
    status: int | None
    detail: str
    trace_id: str | None = None
    instance: str | None = None

    @classmethod
    def from_response(cls, response: HttpResponse) -> BackendApiError:
        try:
            data = response.json()
        except ValueError:
            data = {}

        detail = data.get("detail") if isinstance(data, dict) else None
        trace_id = data.get("traceId") if isinstance(data, dict) else None
        instance = data.get("instance") if isinstance(data, dict) else None
        return cls(
            status=response.status_code,
            detail=detail or response.reason_phrase or "Backend returned an error",
            trace_id=trace_id,
            instance=instance,
        )

    @classmethod
    def unavailable(cls) -> BackendApiError:
        return cls(
            status=None,
            detail="Backend недоступен или не ответил вовремя. Попробуйте позже.",
        )

    def user_message(self) -> str:
        title = {
            400: "Некорректный запрос",
            401: "Ошибка авторизации",
            403: "Доступ запрещён",
            404: "Не найдено",
            409: "Конфликт",
        }.get(self.status, "Ошибка backend" if self.status else "Backend недоступен")

        status_suffix = f" ({self.status})" if self.status is not None else ""
        lines = [f"<b>{title}{status_suffix}</b>", escape(self.detail)]
        if self.trace_id:
            lines.append(f"Trace ID: <code>{escape(self.trace_id)}</code>")
        return "\n".join(lines)
