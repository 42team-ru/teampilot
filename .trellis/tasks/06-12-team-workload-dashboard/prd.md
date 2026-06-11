# Team Workload Dashboard

## Goal

Добавить в mini-app страницу "Нагрузка команды" для менеджера: мини-дашборд, который за 3 секунды показывает кто свободен, кто в норме, кто перегружен — с возможностью перейти к задачам конкретного участника.

## What I already know

* Backend endpoint `GET /teams/{teamId}/workload` — **полностью реализован**, возвращает `List<TeamWorkloadEntry>` с полями `openTaskCount`, `overdueTaskCount`
* Frontend API `teamsApi.getWorkload(teamId)` — **уже есть** в `mini-app/src/api/teams.ts`
* Тип `TeamWorkloadEntry` — **уже есть** в `mini-app/src/api/types.ts`
* Текущий нав: 4 вкладки (Главная, Доска, Команды, Профиль) в `AppLayout.tsx`
* Роль пользователя (MANAGER/PARTICIPANT) есть в `TeamMemberResponse`, но **не хранится** в `appStore`
* `teamsApi.listMyTeams()` возвращает только команды где юзер MANAGER — можно использовать для определения роли

## Assumptions

* Пороги нагрузки: 0–4 задачи = зелёный, 5–8 = жёлтый, 9+ = красный
* Вкладка видна только если активная команда входит в `listMyTeams()` (пользователь — менеджер)

## Open Questions

(нет)

## Decision (ADR-lite)

**Context**: Нужно решить кому показывать вкладку "Нагрузка".
**Decision**: 5-я вкладка навигации, условно рендерится только когда `listMyTeams()` включает активную команду.
**Consequences**: Обычные участники не видят таб → меньше путаницы. Детекция роли — через уже существующий API вызов, без изменений store.

## Requirements

* Страница `/workload` с отображением нагрузки участников команды
* Метрики вверху: всего задач, перегружены (красные), свободны (зелёные)
* Список участников с прогресс-баром, счётчиком задач и цветовым статусом
* Просроченные задачи отображаются отдельно (overdueTaskCount)
* Кнопка "Посмотреть задачи" → фильтрует доску по участнику (переход на /board с фильтром)

## Acceptance Criteria (evolving)

* [ ] Страница `/workload` доступна и рендерится без ошибок
* [ ] Участники отсортированы по убыванию нагрузки
* [ ] Цветовая индикация работает корректно (зелёный/жёлтый/красный)
* [ ] Метрики-карточки вверху показывают корректные агрегаты
* [ ] Кнопка перехода на доску с фильтром работает

## Definition of Done

* Lint / typecheck зелёный (npm run typecheck / lint)
* Нет регрессий на других страницах
* Работает с реальными данными (empty state если нет участников)

## Out of Scope

* Кнопка "Перераспределить задачи" — не в MVP
* Кнопка "Написать исполнителю" — не в MVP
* Хранение роли в appStore (пока определяем через listMyTeams)
* Граф связей задач

## Technical Notes

* Файлы к изменению:
  - `mini-app/src/pages/WorkloadPage.tsx` (создать)
  - `mini-app/src/router.tsx` (добавить route)
  - `mini-app/src/components/layout/AppLayout.tsx` (добавить таб)
* Иконка для таба: `BarChart2` или `Activity` из lucide-react
* Данные: `useQuery` поверх `teamsApi.getWorkload(activeTeam.id)`
* Пороги можно вынести в константу: `const THRESHOLDS = { ok: 5, overloaded: 9 }`
