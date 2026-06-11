# PRD: Meeting Bot — Voice Q&A Agent (голосовой ассистент в звонке)

## Цель

Участник звонка говорит «**Пилот**, ...» — бот в течение ~10 c отвечает голосом в
звонок, используя данные доски (внутренняя БД через Spring) и семантический поиск
(Qdrant). Преимущественно ≤10 c после конца фразы.

Зависит от: `06-11-telemost-playwright-bot-passive-listener` (бот уже в звонке) и
`06-12-telemost-bot-virtual-microphone-fix-beep-tts-ready` (виртуальный mic-sink готов).

---

## Решения по архитектуре (зафиксированы с заказчиком)

1. **Синхронный HTTP, без Kafka.** Голосовой путь латентно-критичный; Kafka добавляет
   4 хопа, джиттер шины и корреляцию запрос/ответ. Делаем один sync round-trip.
2. **always-listen + STT** для wake-word (готовой модели на русское «Пилот» нет;
   openwakeword по англ. 'pilot' ловит криво). VAD режет речь на фразы, каждую фразу
   STT, ищем «пилот»/«pilot» в тексте.
3. **STT живёт в боте** (следствие always-listen — бот читает каждую фразу). То же
   распознавание уже содержит сам вопрос → второй STT не нужен. Бот шлёт в воркер
   **текст**, получает **аудио**.
4. **Воркер = мозг + голос:** LLM с tool-calling + TTS. Эндпоинт `/voice/answer`:
   `{text, team_id, meeting_id}` → wav.
5. **Доска — внутренняя БД через Spring** (`/tasks`), не YouGile.
6. **Весь облачный стек на одном ключе** `LLM_API_KEY` (OpenRouter) + Groq для STT —
   уже сконфигурировано в `llm-worker/.env`. Работает одинаково локально и в докере.

### Поток

```
telemost-bot (слушает bot_sink_<id>.monitor — речь участников):
  VAD (webrtcvad) режет фразу
   → STT (Groq whisper-large-v3, OpenAI-совместимый)
   → если в тексте есть «пилот»/«pilot»:
        POST {worker}/voice/answer {text, team_id, meeting_id}
         ← audio/wav
        paplay → bot_mic_<id> sink → Chrome отдаёт как микрофон → все слышат

llm-worker  POST /voice/answer:
   text → LLM (gpt-4o-mini) с .bind_tools([...5 tools...])
        → tools дёргают Spring /tasks (httpx) и Qdrant (есть)
        → финальный текст ответа (1-2 предложения, разговорно)
   → TTS (OpenRouter /audio/speech, x-ai/grok-voice-tts-1.0) → wav (pcm→wav)
   → возвращает audio/wav

backend (Spring):
   +GET /tasks/stats?teamId        — счётчики (роль BOT)
   +GET /tasks/voice-query?teamId  — фильтрованный список (роль BOT)
```

---

## Демо-вопросы и tools

| Фраза участника | Tool | Источник |
|---|---|---|
| «Пилот, сколько задач в работе и в беклоге?» | `get_board_overview` | GET /tasks/stats |
| «Пилот, что надо сдать до завтра?» / «что просрочено?» | `list_tasks(due_before/overdue)` | GET /tasks/voice-query |
| «Пилот, что сейчас на Олеге?» | `list_tasks(assignee_name)` | GET /tasks/voice-query |
| «Пилот, есть задача про оплату?» | `search_tasks(query)` | Qdrant (`search_knowledge`/tasks collection) |
| «Пилот, заведи задачу починить логин на Олега до пятницы» | `create_task(title, assignee_name, deadline)` | POST /tasks (LlmTaskCreateEvent), резолв имени переиспользуем из воркера |

Tools-сигнатуры (`llm-worker/llm/voice_agent.py`):

```python
get_board_overview(team_id)                         # счётчики по колонкам/статусам
list_tasks(team_id, *, overdue=False, due_before=None, assignee_name=None, column=None)
search_tasks(team_id, query)                        # Qdrant семантика
create_task(team_id, title, assignee_name=None, deadline=None, description=None)
```

LLM получает текущую дату (для «до завтра/до пятницы» → конкретный Instant) в system-prompt.

---

## Backend (Spring) — новые эндпоинты

Причина: текущий `GET /tasks` фильтрует по `chatId` (Long) и telegramId, а у голосового
агента — `team_id` (UUID). Нужны team-scoped read-эндпоинты под ролью BOT.

```java
@PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
@GetMapping("/stats")          // ?teamId=UUID → {backlog, inProgress, done, overdue, dueToday, dueTomorrow, byColumn:{...}}
@GetMapping("/voice-query")    // ?teamId=UUID&overdue=&dueBefore=&assigneeName=&column= → List<TaskBrief>{title, assignee, deadline, column}
```

- Не считаем удалённые (`deleted=true`) и pending-approval (по необходимости).
- `overdue` = `deadline < now AND completed=false`.
- Сервисные методы в `TaskService` (`statsByTeam`, `voiceQuery`), DTO `TaskStatsResponse`, `TaskBriefResponse`.

---

## llm-worker — изменения

- `infra/tts.py` (НОВЫЙ): `synthesize(text) -> bytes(wav)` через OpenRouter
  `POST /audio/speech` (OpenAI-совместимо). Модель `TTS_MODEL`, голос `TTS_VOICE`,
  `response_format=pcm` → завернуть в WAV-контейнер (16-bit, частота из ответа).
- `infra/backend_client.py` (НОВЫЙ): httpx-клиент к Spring (`BACKEND_URL`, `BOT_SECRET`/
  токен роли BOT) — `get_stats`, `voice_query`, `create_task`.
- `llm/voice_agent.py` (НОВЫЙ): `answer(text, team_id, meeting_id) -> str`. LLM
  (`_cheap` из `chains.py`) + `.bind_tools([...])`, цикл tool-calling (макс 2-3 итерации),
  system-prompt «отвечай 1-2 предложениями, разговорно, по-русски; сегодня <дата>».
- `api.py`: `POST /voice/answer` → `voice_agent.answer(...)` → `tts.synthesize(...)` →
  `Response(content=wav, media_type="audio/wav")`. Таймаут-бюджет, лог латентности по стадиям.
- `settings.py`: `TTS_API_BASE` (default = LLM_API_BASE), `TTS_API_KEY` (default = LLM_API_KEY),
  `TTS_MODEL=x-ai/grok-voice-tts-1.0`, `TTS_VOICE`, `BACKEND_URL`, `BOT_TOKEN`/secret.

## telemost-bot — изменения

- `voice_qa.py` (НОВЫЙ): listener-цикл поверх `bot_sink_<id>.monitor`:
  VAD (webrtcvad) собирает фразу → STT (Groq, OpenAI-совместимый клиент) → если
  триггер → `httpx POST {WORKER_URL}/voice/answer` → ответный wav → `paplay`/ffmpeg в
  `bot_mic_<id>` sink. Анти-эхо: на время проигрывания ответа пауза/гейт записи, чтобы
  бот не услышал сам себя.
- `session_manager.py`: запустить `voice_qa` как третий таск сессии (рядом с
  `_browser_task` и `_record_loop`); прокинуть `sink_name`, `mic_sink_name`, `team_id`.
- `config.py`: `WORKER_URL`, `WHISPER_API_BASE/KEY/MODEL` (Groq), `WAKE_WORDS=["пилот","pilot"]`,
  `VAD_AGGRESSIVENESS`, `VAD_SILENCE_MS`, `MIN_UTTERANCE_MS`.
- deps: `webrtcvad`, `httpx`, `openai` (для STT-клиента).

---

## Latency-бюджет (цель ≤10 c, преимущ. ~6-8 c после конца фразы)

| Этап | Бюджет |
|---|---|
| VAD добор тишины (конец фразы) | 0.5-0.8 c |
| STT (Groq whisper-large-v3) | ~0.3-0.7 c |
| HTTP бот→воркер | <0.1 c (локально/докер) |
| LLM + 1 tool call | 1.5-3 c |
| TTS (OpenRouter) | 0.4-1 c |
| HTTP воркер→бот + paplay | <0.2 c |
| **Итого после конца фразы** | **~3-6 c** |

---

## Scope (MVP)

- [ ] telemost-bot: VAD + STT listener + триггер «пилот» + проигрывание ответа в mic-sink (+ анти-эхо гейт)
- [ ] llm-worker: `POST /voice/answer` (text→wav)
- [ ] llm-worker: `infra/tts.py` (OpenRouter TTS)
- [ ] llm-worker: `infra/backend_client.py` + `llm/voice_agent.py` с 5 tools
- [ ] Spring: `GET /tasks/stats`, `GET /tasks/voice-query` (роль BOT, teamId)
- [ ] Конфиг/env: TTS_MODEL/VOICE, WORKER_URL, WHISPER на боте; docker-compose проброс
- [ ] Логи латентности по стадиям

## Out of scope

- Kafka voice-топики (отказались в пользу sync HTTP)
- Кастомная wake-модель на «Пилот» (always-listen+STT покрывает)
- Вывод видео/картинки в звонок
- Многопользовательская диаризация / «кто спросил»

## Риски

- **Эхо**: бот слышит собственный TTS-ответ → ложный повторный триггер. Митигируем
  гейтом записи на время проигрывания (+ небольшой хвост).
- **Шум always-listen**: много коротких фраз → лишние STT. Фильтр по `MIN_UTTERANCE_MS`
  и наличию «пилот» в начале/тексте.
- **Резолв имени ассайни** («Олег» → TeamUser): переиспользовать логику воркера; при
  неоднозначности — переспросить голосом или отдать без ассайни.
- **headless без Xvfb**: PulseAudio-роутинг может не работать (уже есть warning).

## Стек

- telemost-bot: Python 3.12, webrtcvad, ffmpeg/paplay (PulseAudio), httpx, openai (STT→Groq)
- llm-worker: FastAPI, langchain-openai (LLM, OpenRouter), httpx (Spring), qdrant-client, OpenRouter TTS
- backend: Java 21 / Spring Boot, новые BOT-эндпоинты
