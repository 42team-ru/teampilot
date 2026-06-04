# log-full-url-in-http-request-error

## Goal

В логе бота при ошибке HTTP-запроса сейчас видно только относительный путь (`path=/users/713978344`).
Нужно логировать полный URL (`path=http://localhost:8080/users/713978344`), чтобы было сразу понятно,
к какому хосту и порту шёл запрос.

## Requirements

* В `log_http_request_error` и `log_http_response_error` вместо `path=<relative>` логируется полный URL.
* Решение: в каждом сервисе передавать `path=f"{settings.BACKEND_URL}{path}"` (Approach A).
* Охват: все вызовы во всех 4 сервисных файлах.

## Acceptance Criteria

* [ ] Лог `Backend request failed` содержит полный URL: `path=http://…/users/713978344`
* [ ] Все вызовы `log_http_request_error` / `log_http_response_error` из бот-сервисов отражают полный URL

## Decision (ADR-lite)

**Context**: `log_http_request_error` принимает `path`, вызывающие передают только относительный путь.
**Decision**: Approach A — передавать `f"{settings.BACKEND_URL}{path}"` на стороне вызывающих, без изменения сигнатуры `http_logging.py`.
**Consequences**: нет усложнения сигнатуры; ~15 мест правки, все тривиальны.

## Out of Scope

* Изменения сигнатуры `http_logging.py`
* Изменения на стороне Spring monolith
* Исправление `/api/tasks` → `/tasks` в `task_service.py` (отдельный баг)

## Affected Files

| Файл | Кол-во мест |
|------|------------|
| `bot/services/admin_service.py` | 3 |
| `bot/services/user_service.py` | 4 |
| `bot/services/team_service.py` | ~8 |
| `bot/services/task_service.py` | 2 |

## Technical Notes

* `log_http_request_error` / `log_http_response_error` — `bot/services/http_logging.py`
* `settings.BACKEND_URL` по умолчанию `http://localhost:8080` (`bot/config.py:9`)
* Swagger (эталон): `http://localhost:8080` — все пути подтверждены
* `team_service.py` также использует прямые `logger.warning(f"...")` в `yougile_auth`/`yougile_select_board` — обновить на `log_http_request_error` для консистентности (в рамках этой задачи)
