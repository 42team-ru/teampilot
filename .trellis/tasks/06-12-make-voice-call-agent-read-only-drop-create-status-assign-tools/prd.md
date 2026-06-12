# Голосовой агент в звонке — только read-only (убрать create/status/assign)

## Цель
Сделать живого голосового агента «Пилот» в звонке **чисто read-only**: отвечать на вопросы
по доске (счётчики/списки/поиск), но НЕ менять доску. Все мутации доски (создание задач,
смена статуса, назначение) выполняются **только** через транскрипционный путь.

## Зачем
- Живые мутации по голосу «долгие»: многократные tool-round'ы LLM + backend-вызовы + TTS
  на каждое создание/изменение → задержка ответа в звонке.
- Покрытие не теряется: транскрипция уже создаёт задачи и меняет статусы независимо и
  **инкрементально по ходу встречи** (`processor.py:_meeting_context_after_chunk` →
  `audio_task_chain` / `audio_status_chain` → `TaskCreateEvent` / `StatusChangeEvent` →
  Spring → YouGile), и эти задачи так же проходят подтверждение в Telegram (`bots.tasks`).

## Что меняем

### llm-worker/llm/voice_agent.py (основное)
- Убрать из `_build_tools` инструменты: `create_task`, `propose_change_status`,
  `propose_assign`, `confirm_action`, `cancel_action`.
- Оставить read-only: `get_context`, `get_board_overview`, `list_tasks`, `search_tasks`,
  `list_team_members`, `list_columns`.
- Удалить состояние `_pending` и всю логику ожидающего подтверждения.
- Переписать `_system_prompt`: убрать блоки про действия/подтверждения; оставить правила
  ответа (по-русски, коротко, голосом, инструменты для данных). Убрать параметр `pending`.
- Упростить `answer()`: убрать передачу `_pending.get(meeting_id)`.

### llm-worker/infra/backend_client.py (чистка мёртвого кода)
- `create_task`, `change_status`, `assign_task` использовались ТОЛЬКО голосовым агентом →
  становятся неиспользуемыми. Удалить их.

## Spring-сторона (сделано в этой же задаче по просьбе пользователя)
- Удалены мутирующие эндпоинты `/tasks/voice-create`, `/voice-status`, `/voice-assign` и
  сервисные методы `voiceCreate` / `voiceChangeStatus` / `voiceAssign` + осиротевшие хелперы
  (`resolveAssignee`, `resolveTaskByTitle`, `resolveColumnByName`, `isDoneColumn`,
  `resolveAssigneeByName`) + DTO запросов (VoiceCreateTaskRequest/Status/Assign).
- Оставлены read-only эндпоинты `/voice-context`, `/voice-members`, `/voice-columns`
  (+ DTO VoiceContextResponse, VoiceMemberResponse) — их дёргает агент.
- `:monolith:compileJava` — зелёный.

## Вне скоупа
- Транскрипционный путь Spring (Kafka: `handleStatusChange` / `createFromLlmEvent`) — НЕ трогаем,
  он и есть замена живых мутаций.

## Критерии приёмки
- Голосовой агент в звонке отвечает на вопросы, но физически не может создать/изменить/назначить.
- Создание задач и смена статусов по итогам встречи продолжают работать (через транскрипцию).
- Нет мёртвого кода `backend_client` (мутирующие функции удалены), llm-worker стартует, импорты целы.
