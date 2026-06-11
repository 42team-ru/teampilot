# Mini App — фикс колонок, профиль со статистикой и ачивками, автовыбор команды

## Goal

Три критических проблемы после первого входа:
1. Доска пустая (колонки не грузятся) — `GET /tasks/columns` требует `chatId`, но у многих команд его нет
2. Профиль не показывает level/XP/streak/ачивки — данные есть в API, типы не прописаны
3. `activeTeam` не выбирается автоматически — пользователь должен вручную идти в Команды и выбирать

## Requirements

### Fix 1 — Колонки доски
- **Backend**: добавить `@RequestParam(required = false) UUID teamId` к `GET /tasks/columns`
  - если `chatId` null → искать команду по `teamId`
- **Frontend**: `tasksApi.listColumns(params: { chatId?: number, teamId?: string })`
- **Frontend**: `useTaskColumns(chatId, teamId)` — передавать `activeTeam.id` как fallback
- **Frontend**: `BoardPage` — передавать оба параметра

### Fix 2 — Профиль со статистикой
- Добавить тип `UserStatsResponse` в `types.ts` (completedCount, overdueCount, onTimeRate, streakDays, xp, level, levelName, xpForCurrentLevel, xpForNextLevel, achievements[])
- Переписать `ProfilePage`:
  - Аватар + имя + @username
  - Уровень (badge с `levelName`) + XP прогресс-бар
  - Сетка статов: ✅ завершено, ⚡ стрик, 🎯 точность в срок
  - Список ачивок (earned → locked)
  - Кнопка выйти внизу

### Fix 3 — Автовыбор команды
- После логина (`OnboardingPage`) — фетчить список команд и автоматически выбирать первую
- В `DashboardPage` — если `activeTeam === null`, показать кнопку "Выбрать команду"

## Technical Approach

**Backend**: `TaskController.listColumns` + `TaskService.listColumns` — добавить `teamId` параметр

**Frontend files**:
- `api/types.ts` — добавить `UserStatsResponse`
- `api/tasks.ts` — изменить `listColumns` сигнатуру
- `hooks/useTasks.ts` — `useTaskColumns(chatId?, teamId?)`
- `pages/BoardPage.tsx` — передавать teamId
- `pages/ProfilePage.tsx` — полный рефакторинг
- `pages/OnboardingPage.tsx` — авто-выбор первой команды после логина

## Out of Scope

- Notification settings
- Courses management
- Knowledge base

## Acceptance Criteria

- [ ] Доска показывает колонки когда YouGile настроен (даже без telegramChatId)
- [ ] Профиль показывает уровень, XP бар, стрик, список ачивок
- [ ] После первого входа activeTeam выбирается автоматически
