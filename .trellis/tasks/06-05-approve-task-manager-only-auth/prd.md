# approve-task-manager-only-auth

## Goal

Метод `TaskService.approve` должен разрешать аппрув задачи только тому пользователю, у которого роль `MANAGER` в команде, к которой принадлежит задача. Все остальные получают 403.

## Requirements

* Перед изменением статуса задачи проверить, что вызывающий `user` является членом команды задачи с ролью `TeamRole.MANAGER`.
* Если пользователь не является членом команды → `AppException.forbidden("You are not a member of this team")`.
* Если пользователь является членом, но с ролью `USER` → `AppException.forbidden("Only a team manager can approve tasks")`.
* Остальная логика метода не меняется.

## Acceptance Criteria

* [ ] Менеджер команды успешно апрувит задачу → статус меняется на ACTIVE.
* [ ] Не-член команды получает 403.
* [ ] Член команды с ролью USER получает 403.
* [ ] Член команды с ролью MANAGER другой команды получает 403.

## Technical Approach

Использовать уже инжектированный `teamUserRepository.findByTeamIdAndUserId(task.getTeam().getId(), user.getId())`:
- не найден → forbidden "not a member"
- найден, но `role != MANAGER` → forbidden "only manager"

Проверка вставляется после загрузки задачи, до изменения статуса.

## Out of Scope

* Изменения в контроллере (авторизация на уровне сервиса, контроллер не трогаем).
* Тесты (хакатон).

## Technical Notes

* `TeamUserRepository.findByTeamIdAndUserId(UUID teamId, UUID userId)` — уже есть.
* `TeamRole.MANAGER` — уже есть.
* `teamUserRepository` уже инжектирован в `TaskService`.
* Файлы: `TaskService.java:75`.
