# make telegram_chat_id nullable in teams

## Goal

Команда создаётся как «заготовка» через `/admin` → `POST /admin/teams` без привязки к Telegram-группе. `telegramChatId` будет задан позже через `PATCH /teams/{teamId}`. Сейчас колонка `telegram_chat_id` объявлена `NOT NULL` в энтити и в БД, что роняет запрос с `ConstraintViolationException`.

## What I already know

* `Team.java`: `@Column(name = "telegram_chat_id", nullable = false, unique = true)` — нужно `nullable = true`
* `ddl-auto: update` — Hibernate НЕ снимет NOT NULL автоматически, нужна ручная миграция
* Flyway в проекте в `libs.versions.toml` есть, но в `build.gradle.kts` monolith — не подключён. `V4__create_uploaded_files.sql` есть, но не применяется (нет зависимости).
* `TeamService.createWithAdmin`: делает `findByTelegramChatId(req.telegramChatId())` — если `null`, Spring Data использует `IS NULL`, что вернёт другую «черновую» команду вместо создания новой.
* Механизм привязки чата позже уже есть: `PATCH /teams/{teamId}` → `UpdateTeamRequest.telegramChatId`
* `AdminCreateTeamRequest.telegramChatId` — уже nullable (`Long`, не примитив), бот никогда не передаёт его.

## Requirements

* `telegram_chat_id` в entity и в БД — nullable
* `TeamService.createWithAdmin`: если `telegramChatId == null` — пропускать lookup, создавать новую команду
* Unique constraint сохраняется (PostgreSQL допускает несколько NULL в UNIQUE-колонке)

## Acceptance Criteria

* [ ] `POST /admin/teams` с телом `{chatTitle, adminTelegramId, adminUsername}` без `telegramChatId` — создаёт команду, HTTP 201
* [ ] Повторный `POST /admin/teams` с тем же `telegramChatId != null` — возвращает/обновляет существующую команду (upsert)
* [ ] `PATCH /teams/{teamId}` с `telegramChatId` — проставляет чат к ранее созданной команде

## Decision (ADR-lite)

**Context**: `ddl-auto: update` не снимает NOT NULL с существующих колонок.
**Decision**: Пользователь пересоздаст БД вручную (`make core-down && make core-up`). Flyway не добавляем.
**Consequences**: Изменения в entity подхватятся при следующем старте с чистой БД.

## Technical Notes

* `backend/monolith/src/main/java/ru/team42/monolith/entity/Team.java:28`
* `backend/monolith/src/main/java/ru/team42/monolith/service/TeamService.java:53-81`
* `backend/monolith/src/main/resources/db/migration/` — существующая директория для миграций
* Flyway dependency alias: `libs.spring.boot.starter.flyway` + `libs.flyway.database.postgresql`
