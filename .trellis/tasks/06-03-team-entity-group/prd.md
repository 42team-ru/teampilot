# Team entity: заменить Group

## Goal

Заменить сущность `Group` (`chat_groups`) на `Team` с дочерними сущностями `TeamUser` и `TaskFromYougile`. Новая модель более явно отражает ролевую систему и хранение задач с YouGile.

## Requirements

- `Team` заменяет `Group`: `telegramChatId`, `kanbanId`, `kanbanApiKey` (+ `chatTitle` для отображения)
- `TeamUser` — связь пользователя с командой: роль (`ADMIN/MANAGER/USER`) + `yougileUserId` (переезжает из `User` сюда)
- `TaskFromYougile` — полумоканная сущность: `yougileId`, `localStatus`, `yougileStatus`, `name`, `description`
- Удалить `chat_groups`, создать `teams`, `team_users`, `tasks_from_yougile` через Flyway-миграцию
- Обновить все слои: entity → repository → service → controller → DTOs
- `User.yougileUserId` и `User.yougileDisplayName` — убрать из `User` (переезжают в `TeamUser`)

## Acceptance Criteria

- [ ] Сущность `Team` заменяет `Group` во всех слоях (entity, repo, service, controller)
- [ ] `TeamUser` хранит роль и `yougileUserId` для каждого участника команды
- [ ] `TaskFromYougile` имеет `yougileId`, `localStatus`, `yougileStatus`, `name`, `description`
- [ ] Flyway-миграция: drop `chat_groups`, create `teams` + `team_users` + `tasks_from_yougile`
- [ ] REST-эндпоинты `GroupController` переименованы в `TeamController`
- [ ] Компилируется, существующие вызовы из бота работают (контракт по ответам не ломается)

## Definition of Done

- Компилируется (`./gradlew build`)
- Flyway-миграция применяется без ошибок
- Нет отсылок к старому `Group` / `chat_groups` в основном коде

## Technical Approach

**Новая структура сущностей:**

```
Team (таблица: teams)
  - UUID id
  - Long telegramChatId (unique, not null)
  - String chatTitle
  - boolean active = true
  - String kanbanId (not null)        ← yougileBoardId
  - String kanbanApiKey (not null)    ← yougileToken (512 chars)
  - List<TeamUser> members
  - List<TaskFromYougile> tasks

TeamUser (таблица: team_users)
  - UUID id
  - Team team (ManyToOne)
  - User user (ManyToOne)
  - TeamRole role  (ADMIN, MANAGER, USER)
  - String yougileUserId

TaskFromYougile (таблица: tasks_from_yougile)
  - UUID id
  - Team team (ManyToOne)
  - String yougileId
  - String name
  - String description (TEXT)
  - TaskLocalStatus localStatus    (ACTIVE, DELETED_FROM_YOUGILE)
  - String yougileStatus           (raw string, синхронизируется с YouGile)
```

**Из User убрать:** `yougileUserId`, `yougileDisplayName`

**Файлы к изменению:**
- `entity/Group.java` → удалить, создать `entity/Team.java`, `entity/TeamUser.java`, `entity/TaskFromYougile.java`
- `repository/GroupRepository.java` → `TeamRepository.java`
- `service/GroupService.java` → `TeamService.java`
- `rest/GroupController.java` → `TeamController.java`
- `dto/GroupRequest.java`, `dto/GroupResponse.java` → Team-варианты
- `entity/User.java` — убрать `yougileUserId`, `yougileDisplayName`
- `service/UserService.java` — убрать `linkToYougile`
- `rest/UserController.java` — убрать `PATCH /api/users/{id}/yougile`
- Новая Flyway-миграция (V4 или V5)

## Out of Scope

- Реализация синхронизации задач с YouGile (issue #9) — только структура
- Логика вечернего синка — не в этой задаче
- Изменения в Python-боте

## Technical Notes

- Паттерн: `AbstractEntity` (UUID, createdAt, updatedAt) — наследовать как обычно
- Flyway: файл `V4__CREATE_TEAM.sql` (или следующий свободный номер)
- `TaskFromYougile` — полумоканная: методы синхронизации оставить заглушками, только структура
- `TeamRole` и `TaskLocalStatus` — Java enums рядом с entity
