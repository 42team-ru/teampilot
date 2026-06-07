# knowledge-base-bot-qa

## Goal

Добавить в Telegram-бот команду `/wiki <запрос>`, которая ищет по базе знаний команды (Qdrant `team_knowledge`) и возвращает релевантные результаты прямо в чат.

## What I already know

- Бот использует **aiogram 3.x**, роутеры регистрируются через `dp.include_router()` в `main.py`
- `get_team_id(chat_id, telegram_id)` в `team_service.py` — уже есть, резолвит chat_id → team_id
- Бот НЕ имеет Qdrant в зависимостях (`bot/pyproject.toml` — только aiogram, aiohttp, confluent-kafka)
- Все сервисы бота обращаются к Spring REST — единый паттерн
- Существующий паттерн команд: `tasks_commands.py` с `@router.message(Command("tasks"))` + Filter
- `config.py` — настройки через pydantic-settings, читается из `.env`
- `team_knowledge` коллекция уже существует (создана в task 1)

## Decision (ADR-lite)

**Context**: бот не имеет доступа к Qdrant — нужно выбрать как делать поиск.

**Decision**: **Вариант A — FastAPI HTTP-сервер внутри llm-worker**.
- llm-worker уже имеет всю логику Qdrant + embeddings
- Добавить `fastapi` + `uvicorn` в llm-worker, запустить HTTP в отдельном треде рядом с Kafka-консьюмерами
- Эндпоинт: `GET /knowledge/search?team_id=X&q=text`
- Бот вызывает через `http_client` как обычный REST, без новых зависимостей в боте

**Consequences**: llm-worker теперь HTTP + Kafka. Зато никаких новых сервисов, никакого дублирования конфига Qdrant/embeddings.

## Requirements

**llm-worker (новый HTTP-сервер):**
- [ ] `llm-worker/pyproject.toml` — добавить `fastapi`, `uvicorn`
- [ ] `llm-worker/api.py` — FastAPI-приложение с `GET /knowledge/search?team_id=X&q=text`
- [ ] `llm-worker/main.py` — запустить `uvicorn` в отдельном daemon-треде при старте
- [ ] `llm-worker/settings.py` — добавить `HTTP_PORT: int = 8001`

**bot (клиент):**
- [ ] `bot/config.py` — добавить `LLM_WORKER_URL: str = "http://llm-worker:8001"`
- [ ] `bot/services/knowledge_service.py` — `async search_knowledge(query, team_id, limit=5)` → вызывает llm-worker REST
- [ ] `bot/handlers/knowledge.py` — хендлер `/wiki <запрос>` (group + private)
- [ ] В group chat: резолвит `team_id` через `get_team_id(chat.id)`, ищет, отвечает в чат
- [ ] В private chat: резолвит через `get_member_teams(user_id)`, берёт первую команду
- [ ] Нет результатов → "По запросу «…» ничего не найдено в базе знаний команды."
- [ ] Нет team_id → "Используйте в групповом чате команды."
- [ ] Пустой запрос (только `/wiki`) → "Укажи запрос: /wiki что решили по деплою"
- [ ] `bot/main.py` — зарегистрировать `knowledge_router`

## Acceptance Criteria

- [ ] `/wiki что решили по релизу` в группе → возвращает список с типом и содержимым знаний
- [ ] `/wiki` без запроса → "Укажи запрос: /wiki что решили по деплою"
- [ ] Нет результатов → человекочитаемое сообщение
- [ ] Нет team_id (нелинкованный чат) → корректная ошибка

## Definition of Done

- Все файлы созданы/обновлены
- Импорты не сломаны
- Хендлер зарегистрирован в `main.py`

## Out of Scope

- Пагинация результатов (вернуть top-5, без кнопок "ещё")
- Фильтрация по типу знания через команду (`/wiki --type decision ...`)
- Добавление знаний через бот вручную
- Spring REST эндпоинт для knowledge search

## Technical Notes

- `knowledge_service.py` использует `openai.AsyncOpenAI` для embeddings (не langchain — лишняя зависимость)
- `qdrant_client.AsyncQdrantClient` для async поиска
- Формат ответа: HTML (бот настроен на `ParseMode.HTML`)
- Иконки по типу: `meeting_summary` → 📝, `decision` → ✅, `task_archive` → 📌, `file_summary` → 📄
- Команда в group: `F.chat.type.in_({"group", "supergroup"})`; в private: `F.chat.type == "private"`

## Open Questions

- (нет — всё решено)
