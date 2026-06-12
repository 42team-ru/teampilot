# Голосовые действия Пилота: смена статуса и назначение

## Цель
Дать голосовому агенту «Пилот» (в звонке Telemost) возможность не только отвечать и
создавать задачи, но и **менять статус** задачи (двигать по колонкам / «выполнено») и
**назначать/переназначать** исполнителя — с **голосовым подтверждением** перед мутацией.

## Что уже есть (не трогаем)
- `telemost-bot/voice_qa.py` — захват аудио звонка, STT (Groq Whisper), вызов `voice_agent.answer()`, TTS ответа в звонок.
- `llm-worker/llm/voice_agent.py` — tool-calling агент с инструментами: `get_board_overview`, `list_tasks`, `search_tasks`, `create_task`.
- `llm-worker/infra/backend_client.py` — `get_stats`, `voice_query`, `create_task` (POST `/tasks/voice-create`).
- Spring `TaskController` — `/tasks/voice-create`, `/voice-query`, `/stats`, `/columns`.
- `YouGileService.updateTask(team, task)` — пушит колонку + исполнителей в YouGile. **Это и есть механизм мутации.**

## Решения (брейншторм 2026-06-12)
1. **Поиск + подтверждение голосом.** Агент находит задачу (семантически), переспрашивает
   («Двинуть «X» в Готово, верно?»), действие — после «да». Защита от ошибок распознавания.
2. **Объём сейчас:** только смена статуса + назначение (без дедлайна/удаления).

## Архитектурный нюанс: подтверждение через состояние сессии
Каждая фраза в звонке = отдельный `answer()` без памяти. Подтверждение «да/нет» в следующей
фразе требует **pending-действия на `TelemostSession`**:
- агент решает мутировать → возвращает не действие, а «предложение» (proposed action: тип,
  task_id, target) + озвучку-вопрос;
- бот (`voice_qa`) сохраняет pending на сессии и спрашивает;
- следующая фраза: если утвердительная («да/давай/подтверждаю/верно») и есть pending —
  бот вызывает исполняющий эндпоинт; если отрицательная/иная — pending сбрасывается.

## Скоуп изменений
### Spring (backend/monolith)
- `TaskService.voiceChangeStatus(teamId, taskTitle, columnName)` — найти задачу по названию
  в команде, найти колонку по имени, сменить `task.column`, persist, `YouGileService.updateTask`.
- `TaskService.voiceAssign(teamId, taskTitle, assigneeName)` — найти задачу, найти `TeamUser`
  по имени, назначить, persist, `updateTask`.
- `TaskController`: `POST /tasks/voice-status`, `POST /tasks/voice-assign` (+ request-records).
- Резолв задачи по названию: contains/ilike в рамках team; при неоднозначности — вернуть кандидатов.
- Ошибки — через `AppException` (notFound / badRequest), как в проекте.

### llm-worker
- `infra/backend_client.py`: `change_status(team_id, task_title, column)`, `assign_task(team_id, task_title, assignee_name)`.
- `llm/voice_agent.py`: 2 новых `@tool` (`propose_change_status`, `propose_assign`) — НЕ мутируют
  напрямую, а возвращают предложение для подтверждения; правка системного промпта (объяснить
  агенту цикл «найти → переспросить → по согласию вызвать execute»).
- API/механика pending-состояния между `voice_qa` и агентом (через `/voice/answer` ответ с
  полем pending или отдельный confirm-эндпоинт).

## Критерии приёмки
- В звонке: «Пилот, двинь задачу про оплату в работу» → агент находит, переспрашивает,
  по «да» задача меняет колонку в YouGile.
- «Пилот, назначь задачу про оплату на Олега» → аналогично, исполнитель меняется.
- Ошибка распознавания/«нет» → ничего не мутируется.
- Создание задач (`create_task`) продолжает работать как раньше.

## Вне скоупа
Дедлайны голосом, удаление задач, мультиязычность wake word, оффлайн-режим (openWakeWord).
