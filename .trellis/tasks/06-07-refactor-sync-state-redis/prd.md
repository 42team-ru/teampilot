# Refactor SyncStateService: in-memory → PostgreSQL

## Goal

Заменить in-memory `ConcurrentHashMap` в `SyncStateService` на PostgreSQL + JPA репозитории. Сессии синка и состояния пользователей будут persist-ными: рестарт Spring-сервиса между 18:00 и 19:00 не потеряет данные. Никаких новых сервисов — PostgreSQL уже в стеке.

## What I already know

* `SyncStateService` хранит состояние в 3 ConcurrentHashMap:
  1. `Map<UUID, TeamSyncSession>` — сессии синка (teamId → session)
  2. `Map<Long, UUID>` chatIdToTeamId — вторичный индекс
  3. `Map<String, Long>` requestIdToUser — вторичный индекс
* `TeamSyncSession` содержит `Map<Long, UserSyncState>` с вложенным `List<DraftItem>`
* PostgreSQL уже в стеке, JPA уже настроен, `AbstractEntity` есть
* CLAUDE.md: **НЕ писать Flyway-миграции**, DDL через `ddl-auto: update`
* `SyncStateService` вызывается из: `EveningSyncService`, `SyncController`, `SyncDraftConsumer`
* `ExcuseService` (из прошлой задачи) — тоже in-memory, тот же класс проблем

## Assumptions

* Публичный API `SyncStateService` сохраняется — drop-in замена без изменения вызывающих
* `List<DraftItem>` хранится как JSONB-колонка (через Jackson + `@Column(columnDefinition = "jsonb")`)
* Старые сессии удаляются при `closeSession()` — никакого `@Scheduled` cleanup не нужно
* TTL не нужен — сессия либо закрыта явно, либо переоткрыта при следующем синке

## Requirements

* Новые JPA-сущности (не наследуют `AbstractEntity` — нужен кастомный PK):
  * `SyncSession` — `@Entity`, PK = `teamId` (UUID), поля: `chatId`, `startedAt`
  * `SyncUserState` — `@Entity`, PK = UUID, FK → `SyncSession`, поля: `telegramId`, `username`, `status` (enum), `rawText`, `requestId` (unique index), `draftJson` (JSONB), `confirmedTasksCount`, `pendingTasksCount`
* Новые репозитории:
  * `SyncSessionRepository extends JpaRepository<SyncSession, UUID>`
    * `findByChatId(Long)` — для `getTeamIdByChatId()`
  * `SyncUserStateRepository extends JpaRepository<SyncUserState, UUID>`
    * `findBySessionTeamId(UUID)` — для `getUserStates()`
    * `findByRequestId(String)` — для `getUserByRequestId()`
    * `findBySessionTeamIdAndTelegramId(UUID, Long)` — для `getUserState()`
* `SyncStateService` переписывается через репозитории, публичный API без изменений
* `ExcuseService` мигрирует в PostgreSQL тоже (простая таблица `sync_excuses`)
* `ExcuseSession` — `@Entity`: `telegramId`, `teamId`, `reason`, `date` (LocalDate)

## Acceptance Criteria

* [ ] Вечерний синк сохраняет сессию в PostgreSQL (`sync_sessions` таблица создана DDL)
* [ ] После рестарта Spring между 18:00–19:00 — сессия не теряется, синк продолжается
* [ ] `closeSession()` удаляет все записи из БД (SyncSession + SyncUserState каскадно)
* [ ] `ExcuseService` хранит отмазки в `sync_excuses`, переживает рестарт
* [ ] Все вызывающие (`EveningSyncService`, `SyncController`) работают без изменений кода
* [ ] BUILD SUCCESSFUL

## Definition of Done

* BUILD SUCCESSFUL (Java compile)
* `/test_sync` и `/test_sync_summary` работают end-to-end

## Technical Approach

**Схема (DDL через ddl-auto: update):**

```
sync_sessions
  team_id UUID PK
  chat_id BIGINT UNIQUE
  started_at TIMESTAMPTZ

sync_user_states
  id UUID PK
  team_id UUID FK → sync_sessions(team_id) ON DELETE CASCADE
  telegram_id BIGINT
  username VARCHAR
  status VARCHAR  (AWAITING/DRAFT_SENT/CONFIRMED/REJECTED/EXCUSED)
  raw_text TEXT
  request_id VARCHAR UNIQUE
  draft_json JSONB
  confirmed_tasks_count INT
  pending_tasks_count INT

sync_excuses
  id UUID PK
  telegram_id BIGINT
  team_id UUID
  reason VARCHAR
  excuse_date DATE
```

**SyncStateService** — thin facade: каждый метод делегирует в репозитории под `@Transactional`.

## Decision (ADR-lite)

**Context**: In-memory state теряется при рестарте. Нужен persistence.
**Decision**: PostgreSQL + JPA (уже в стеке), не Redis (нет в проекте, новый сервис).
**Consequences**: Простой путь, все паттерны уже есть. Overhead БД несущественен для 10–100 юзеров в синке.

## Out of Scope

* Redis
* Flyway-миграции
* Concurrent writes safety (достаточно `@Transactional`)
* Cleanup scheduler (сессии закрываются явно)

## Technical Notes

* `AbstractEntity` даёт UUID PK — но для `SyncSession` PK = `teamId` (не генерированный), поэтому не наследуем
* JSONB для `draft`: `@JdbcTypeCode(SqlTypes.JSON)` + `@Column(columnDefinition = "jsonb")` — уже используется в `Task.java` (stickers поле), Hibernate 6 built-in, внешних зависимостей не нужно
* `@OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)` на `SyncSession.userStates`
* Lookup `requestId → userId`: через `SyncUserStateRepository.findByRequestId(String)`
