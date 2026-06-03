# feat: upload audio by team id with team selection in bot

## Goal

При загрузке аудио/видео через бота (кнопка «Загрузить» в панели участника или команда `/upload`)
пользователь сначала выбирает команду, к которой привязывается файл.
Бэкенд сохраняет `team_id` вместе с загруженным файлом, чтобы задачи по транскрипции
обрабатывались в контексте нужной команды.

## What I already know

* **Бот — точка входа**: `member:upload` callback (`handlers/member.py:34`) сразу ставит
  `FileUploadStates.waiting_for_file`; команда `/upload` (`handlers/upload.py:36`) — тоже.
  Никакого шага выбора команды нет.
* **Kafka-путь**: бот загружает файл в MinIO, публикует `FileUploadedEvent` в топик `FILES_UPLOADED`.
  Python-модель (`models/events.py:29`) не содержит `team_id`.
* **Бэкенд Kafka**: `FileUploadConsumer` → `FileUploadService.save()` → `UploadedFile`.
  Java-модель `FileUploadedEvent.java` не содержит `teamId`.
  Таблица `uploaded_files` (V4 миграция) — нет колонки `team_id`.
* **REST-путь** (`AudioController POST /audio/upload`) — отдельная ветка для транскрипции,
  бот в ней НЕ участвует (не вызывает этот endpoint). Пока вне скоупа.
* **Список команд**: `get_my_teams(telegram_id)` уже реализован (`services/team_service.py:40`),
  клавиатура `manager_team_select_keyboard` уже есть (`keyboards/manager.py:22`).
* **FSM-состояния**: `FileUploadStates` имеет только `waiting_for_file`; нужно добавить
  `waiting_for_team_select`.

## Open Questions

*(нет)*

## Requirements

1. При нажатии кнопки «Загрузить» (callback `member:upload`) и при вызове `/upload`
   сначала отображается список команд пользователя.
2. Пользователь выбирает команду — `team_id` сохраняется в FSM.
3. После выбора команды запрашивается файл (как сейчас).
4. `FileUploadedEvent` (Python и Java) содержит поле `team_id` / `teamId`.
5. `FileUploadService.save()` ищет команду по `teamId` и линкует к `UploadedFile`.
6. Новая Flyway-миграция добавляет nullable `team_id UUID REFERENCES teams(id)`
   в таблицу `uploaded_files`.

## Acceptance Criteria

* [ ] Кнопка «Загрузить» → показывается список команд (inline кнопки)
* [ ] `/upload` команда → тоже показывает список команд
* [ ] После выбора команды — запрос файла как обычно
* [ ] `FileUploadedEvent` несёт `team_id`
* [ ] `UploadedFile` в БД заполнен `team_id`
* [ ] Если у пользователя 0 команд → сообщение «У вас нет доступных команд» и выход из флоу
* [ ] Бэкенд отклоняет событие/запрос без `team_id` (404 или badRequest)

## Definition of Done

* Тесты добавлены/обновлены там, где применимо
* Миграция flyway корректна
* Kafka-событие обратно-совместимо (поле nullable)

## Out of Scope (explicit)

* Пагинация в списке команд > 8
* Пагинация в списке команд (есть лимит 8 в `manager_team_select_keyboard`)
* Изменение UX для группового чата (только личка бота)

## Decision (ADR-lite)

**Context**: файл при загрузке не привязан к команде — LLM-пайплайн не знает, в контексте какой команды создавать задачи.
**Decision**: `teamId` обязателен и в Kafka-пути (`FileUploadedEvent`), и в REST-пути (`AudioController`). Бот показывает шаг выбора команды перед загрузкой.
**Consequences**: `team_id` nullable в БД (FK может отсутствовать если событие пришло без teamId из старого кода), но новые записи всегда будут заполнены.

## Technical Notes

### Бот
* `states/upload.py` — добавить `waiting_for_team_select = State()`
* `handlers/member.py:34` `member_upload` — вместо set_state(waiting_for_file) → вызов хелпера показа команд
* `handlers/upload.py` — добавить обработчик callback `upload:team_select:<team_id>`,
  команда `/upload` тоже через шаг выбора команды
* `keyboards/upload.py` (новый) — `upload_team_select_keyboard(teams)` с action `upload:team_select`
  (отдельный prefix, не смешиваем с `manager:` callbacks)
* `models/events.py FileUploadedEvent` — `team_id: str | None = None`
* `handlers/upload.py handle_upload_file` — читает `team_id` из FSM data, пишет в event

### Бэкенд — Kafka-путь
* `kafka-common FileUploadedEvent.java` — добавить `@JsonProperty("team_id") String teamId`
* `UploadedFile.java` — `@ManyToOne(fetch=LAZY) @JoinColumn(name="team_id") Team team`
* `FileUploadService.save()` — lookup `teamRepository.findById(UUID.fromString(event.getTeamId()))`
* Миграция `V6__add_team_id_to_uploaded_files.sql` — `team_id UUID REFERENCES teams(id)`

### Бэкенд — REST-путь
* `AudioController POST /audio/upload` — добавить `@RequestParam UUID teamId`
* `AudioService.upload(file, teamId)` — принять teamId, найти Team, сохранить в `AudioFile`
* `AudioFile.java` — `@ManyToOne(fetch=LAZY) @JoinColumn(name="team_id") Team team`
* Миграция `V7__add_team_id_to_audio_files.sql` — `team_id UUID REFERENCES teams(id)`
