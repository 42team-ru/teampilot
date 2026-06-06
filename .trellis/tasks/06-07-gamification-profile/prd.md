# Gamification and Profile

## Context

Add MVP RPG gamification to the Telegram task workflow:

- XP for completed tasks
- computed levels and level names
- daily completion streak
- achievements
- `/profile` command in the bot
- backend stats endpoint for bot consumption
- direct bot notifications for achievements and level-ups

The only new persisted gamification state is `UserProfile` and
`UserAchievement`. All stats should be derived from existing task data where
possible.

## Backend Requirements

### Domain Model

Add `UserProfile` in the monolith entity package:

- table: `user_profiles`
- extends `AbstractEntity`
- one-to-one user relation through `user_id`, unique
- fields:
  - `xp: long`, default `0`
  - `streak: int`, default `0`
  - `lastActiveDate: LocalDate`, nullable

Add `UserAchievement`:

- table: `user_achievements`
- extends `AbstractEntity`
- many-to-one user relation through `user_id`
- `achievementKey: String`
- `awardedAt: Instant`
- unique constraint on `(user_id, achievement_key)`

Add `AchievementType` enum under `entity/enums` with:

- enum key
- emoji
- Russian display name
- Russian description
- XP reward

MVP achievements:

| Key | Emoji | XP | Condition |
|---|---:|---:|---|
| `FIRST_STEP` | target emoji | 50 | first completed task |
| `LIGHTNING` | lightning emoji | 100 | completed in less than 50% of allocated time when timing data is available |
| `EARLY_BIRD` | runner emoji | 75 | completed at least 24 hours before deadline |
| `WEEK_STREAK` | fire emoji | 100 | streak is at least 7 days |
| `SNIPER` | target emoji | 150 | last 10 completed tasks are on time |
| `MOUNTAIN` | mountain emoji | 200 | 50 completed tasks total |
| `CLEAN_MONTH` | snowflake emoji | 200 | no overdue tasks in the last 30 days |

Do not implement `TEAM_PLAYER`, `FASTEST`, or `VOICE` in this MVP.

### Repositories

Add `UserProfileRepository`:

- `Optional<UserProfile> findByUserTelegramId(Long telegramId)`
- `Optional<UserProfile> findByUserId(UUID userId)`

Add `UserAchievementRepository`:

- `List<UserAchievement> findByUserId(UUID userId)`
- `boolean existsByUserIdAndAchievementKey(UUID userId, String key)`

Extend `TaskRepository` with queries for gamification stats:

- count completed tasks for a Telegram user
- count completed overdue tasks
- count still-open overdue tasks
- fetch the latest 10 completed tasks for `SNIPER`
- count overdue tasks after a supplied instant for `CLEAN_MONTH`

Use existing task timestamps carefully. `updatedAt` may be used as the completion
time proxy because task completion saves the task and JPA auditing updates it.

### Service

Add `GamificationService` with:

- `void onTaskCompleted(Task task)`
- `UserStatsResponse getUserStats(Long telegramId)`
- static level helpers for:
  - level from XP
  - level name
  - XP floor for current level
  - XP floor for next level

`onTaskCompleted` behavior:

- no-op when task has no assignee or no assignee user
- get or create profile for the assignee user
- capture previous level before XP changes
- update streak in UTC
- compute task XP:
  - on time: `100`
  - late or no deadline: `20`
  - early by at least 24h: `+50`
  - streak multiplier: `min(1.0 + (streak - 1) * 0.1, 2.0)`
- save XP to profile
- check achievements and award only missing ones
- achievement reward XP is added to the same profile
- publish `ACHIEVEMENT` notifications for newly awarded achievements
- publish `LEVEL_UP` notifications only when total XP crosses into a new level
- do not send ordinary task-XP notifications

Achievement conditions should be conservative when required data is missing.
For example, skip `LIGHTNING` if there is no reliable start/assignment time.

### API

Add `UserStatsResponse`:

- `completedCount`
- `overdueCount`
- `onTimeRate` from `0.0` to `1.0`
- `streakDays`
- `xp`
- `level`
- `levelName`
- `xpForCurrentLevel`
- `xpForNextLevel`
- `achievements`

Nested achievement DTO:

- `key`
- `emoji`
- `name`
- `awardedAt`

Add endpoint in `UserController`:

- `GET /users/{telegramId}/stats`
- returns `ResponseUtils.ok(gamificationService.getUserStats(telegramId))`

### Task Completion Hook

In `TaskService.applyComplete()`, after the task is saved and synchronized with
YouGile, call gamification inside `try/catch`:

- `gamificationService.onTaskCompleted(saved)`
- log a warning and do not fail task completion if gamification fails

### Kafka Event Contract

Extend Java `BotNotificationEvent` with nullable fields serialized in camelCase:

- `achievementName`
- `achievementEmoji`
- `xpGained`
- `newTotalXp`
- `newLevelName`

Support new event types:

- `ACHIEVEMENT`
- `LEVEL_UP`

Publish through the existing `bots.notifications` topic and existing
notification publisher infrastructure.

## Bot Requirements

### Event Model

Extend `bot/models/events.py` `BotNotificationEvent` with aliases matching
Spring camelCase serialization:

- `achievement_name`
- `achievement_emoji`
- `xp_gained`
- `new_total_xp`
- `new_level_name`

### Kafka Consumer

In `_send_bot_notification()`, render:

- `ACHIEVEMENT`: direct message about new achievement and XP reward
- `LEVEL_UP`: direct message about new level and total XP

Use HTML escaping for dynamic values.

### Profile Service

Add `bot/services/profile_service.py` with:

- `get_user_stats(telegram_id: int, client: HttpClient) -> dict`
- request path: `/users/{telegram_id}/stats`
- include `X-Telegram-Id` header

### Profile Handler

Add `bot/handlers/profile.py`:

- `/profile` command
- fetch stats for `message.from_user.id`
- render HTML profile card with:
  - level and level name
  - XP progress bar
  - completed count
  - overdue count
  - on-time percentage
  - streak days
- inline keyboard with achievements button
- callback `profile:achievements` renders awarded achievements

Register profile router in `bot/main.py` before the group router.

### Levels

Do not persist levels. Derive them from total XP:

| Level | XP from | Name |
|---:|---:|---|
| 1 | 0 | Новобранец |
| 2 | 400 | Исполнитель |
| 3 | 900 | Специалист |
| 4 | 1600 | Профессионал |
| 5 | 2500 | Эксперт |
| 6 | 3600 | Легенда |

Use:

- `xpForCurrentLevel = level * level * 100`
- `xpForNextLevel = (level + 1) * (level + 1) * 100`
- level is capped at 6

For level 1, current floor must be `0`, not `100`.

## Acceptance Criteria

- Completing a task creates or updates `user_profiles`.
- Completing a first task awards `FIRST_STEP`.
- XP increases according to task timing and streak multiplier.
- Achievements are unique per user.
- Level-up and achievement events are published to `bots.notifications`.
- Python bot parses new notification fields using camelCase aliases.
- `/profile` renders without crashing for users with no achievements.
- `GET /users/{telegramId}/stats` returns complete stats JSON.
- Existing task completion remains successful even if gamification fails.
- Backend build/tests and bot checks pass or any unavailable checks are documented.
