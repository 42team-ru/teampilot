# Telegram Mini App Frontend

## Goal

Разработать Telegram Mini App (TMA) как полноценный веб-клиент для TeamPilot-бота.
Приложение заменяет и дополняет бота: управление командами, задачи в канбан-формате,
вечерний дайджест, настройка YouGile, онбординг — всё в одном месте внутри Telegram.

## Requirements

### Стек
- React 19 + Vite + TypeScript
- shadcn/ui + TailwindCSS (v3, как в extension/)
- `@tma.js/sdk-react` — Telegram Web App SDK
- TanStack Query v5 — server state + кэш
- Zustand — глобальный UI-стейт (тема, активная команда, онбординг-флаги)
- React Hook Form + Zod — формы и валидация
- `@dnd-kit/core` — drag-and-drop на канбан-доске
- React Router v6 — клиентская навигация
- `sonner` — toast-уведомления

### Страницы и функционал

#### Onboarding (первый запуск)
- Автологин через `initData` → `POST /auth/telegram`
- Нет команд → экран с двумя CTA: создать команду (оплата) / войти по инвайту
- Wizard подключения YouGile (2 шага: auth + выбор доски)

#### Bottom Navigation (5 табов)
1. `/` — Dashboard
2. `/board` — Kanban
3. `/sync` — Вечерний дайджест
4. `/teams` — Команды
5. `/profile` — Профиль

#### Dashboard `/`
- Счётчики просроченных / на сегодня задач
- Список моих задач (GET /tasks/my)
- Лента активности команды
- Свайп карточки вправо → быстро завершить задачу

#### Kanban `/board`
- Горизонтальный скролл колонок (GET /tasks/columns + GET /tasks)
- Фильтр по участнику (ToggleGroup)
- Drag-and-drop карточек между колонками (@dnd-kit) → PATCH /tasks/{id}/column
- Tap на карточку → Sheet с деталями
- FAB кнопка создания задачи

#### Task Detail (Sheet)
- Просмотр и редактирование задачи
- Смена статуса/колонки (PATCH /tasks/{id})
- Смена assignee, дедлайна
- Approve / Cancel
- Telegram MainButton = "Сохранить" при наличии изменений

#### Create Task (Sheet)
- Форма: title, description, assignee (Command-поиск), deadline (Calendar), priority, tag
- POST /tasks (нужен новый DTO на бэке — не LlmTaskCreateEvent)
- Telegram MainButton = "Создать"

#### Sync / Дайджест `/sync`
- GET /sync/active-tasks
- Approve / Reject задач и пропозалов
- Кнопка "Пропустить сегодня" → POST /sync/excuse

#### Teams `/teams`
- Список команд: менеджер + участник (GET /teams/my + /teams/member-of)
- Team Detail Sheet: участники, настройки, файлы, YouGile доска
- Управление участниками: кик, смена роли
- Генерация инвайт-ссылки (POST /auth/invite)
- Смена YouGile доски (PATCH /auth/invite/{teamId}/yougile)

#### Profile `/profile`
- Профиль и статистика (GET /users/{telegramId}/stats)
- PATCH /users/me (имя)
- Настройки уведомлений (GET/PATCH /notifications/settings — через бота)

### UX принципы
- Тема: читаем `colorScheme` из Telegram SDK → dark/light → CSS переменные
- Haptic feedback (`HapticFeedback`) на ключевые действия
- Telegram BackButton → назад / закрыть Sheet
- Telegram MainButton → primary CTA на формах
- Оптимистичные обновления через TanStack Query
- Skeleton loaders на каждом блоке

### Аутентификация
- `window.Telegram.WebApp.initData` → заголовок `X-Telegram-Init-Data` на все запросы
- Бэкенд верифицирует HMAC-SHA256

## Acceptance Criteria

- [ ] Автологин работает при открытии Mini App из бота
- [ ] Онбординг (инвайт + YouGile) проходится без бота
- [ ] Kanban отображает задачи и колонки команды
- [ ] Drag-and-drop меняет колонку задачи
- [ ] Task Detail Sheet: просмотр, редактирование, смена статуса
- [ ] Создание задачи из формы
- [ ] Вечерний дайджест: approve/reject работают
- [ ] Управление командой: участники, роли, инвайт
- [ ] Темизация следует теме Telegram (dark/light)
- [ ] Haptic feedback на создании/смене статуса/удалении

## Definition of Done

- TypeScript строгий (noImplicitAny, strict)
- Lint (ESLint) и typecheck чистые
- Сборка `npm run build` успешна
- Работает в Telegram WebView (iOS + Android)
- Docker-сервис добавлен в docker-compose.services.yml

## Out of Scope

- Offline / PWA режим
- Push-уведомления через Mini App (есть у бота)
- Полная замена YouGile (только нужные операции)

## Technical Notes

### Структура директорий (планируется)
```
mini-app/
  src/
    api/          — axios-клиент + хуки TanStack Query
    components/   — переиспользуемые компоненты
    pages/        — страницы по роутам
    stores/       — Zustand сторы
    lib/          — утилиты, cn(), tg-helpers
  public/
  index.html
  vite.config.ts
  package.json
```

### Существующий стек в репо
- `extension/` — WXT + React 19 + Tailwind v3 + Radix UI (shadcn базис)
  Те же зависимости: clsx, tailwind-merge, class-variance-authority, lucide-react
  → можно переиспользовать shadcn-компоненты как образец

### API — добавляем в рамках этой задачи
- `PATCH /tasks/{id}` — обновление задачи (columnId, assigneeId, deadline, title, description)
- `POST /tasks` с user-friendly DTO (не LlmTaskCreateEvent) — CreateUserTaskRequest

#### Spring: PATCH /tasks/{id}
- `UpdateTaskRequest` DTO: `columnId?`, `assigneeId?`, `deadline?`, `title?`, `description?`
- Частичное обновление (null = не менять)
- Только authenticated пользователь, проверка доступа к задаче через команду
- Синхронизация с YouGile при смене колонки (как существующий `/tasks/{id}/sync`)

### Docker / Hosting
- Caddy раздаёт статику (file_server) — отдельный контейнер не нужен
- Сборка `mini-app/dist/` монтируется в Caddy-контейнер
- HTTPS через Caddy auto-TLS (обязательно для Telegram Mini Apps)
- Маршрут: `https://<domain>/app/*` → static files

## Decisions

- **PATCH /tasks/{id}**: реализуем в рамках этой задачи (Spring + фронт)
- **Хостинг**: Caddy file_server — отдельный контейнер не нужен
- **URL**: настраивается через @BotFather после деплоя (runtime, не в коде)
