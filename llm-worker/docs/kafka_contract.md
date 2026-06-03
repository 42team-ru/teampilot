# Контракты Kafka: Входные и Выходные данные LLM Worker

Этот документ описывает, **что мы ожидаем на вход** от Spring-бэкенда и **в каком виде мы отдаём** данные обратно в Kafka.

---

## Входные данные (Spring → LLM Worker)

LLM Worker слушает топик `messages.batches` (задаётся через `KAFKA_TOPIC_IN`).

Spring-бэкенд собирает сообщения за последние несколько минут из чата, добавляет список участников команды и отправляет батчем.

### Полный пример входного JSON

```json
{
  "event_id": "unique-batch-12345",
  "occurred_at": "2026-06-03T15:00:00+03:00",
  "chat_id": 1001,
  "batch_start": "2026-06-03T14:55:00+03:00",
  "batch_end": "2026-06-03T15:00:00+03:00",
  "team": [
    {
      "user_id": 204,
      "username": "@pm_ivan",
      "full_name": "Иван Менеджеров",
      "role": "PM"
    },
    {
      "user_id": 201,
      "username": "@frontend_kirill",
      "full_name": "Кирилл Версталов",
      "role": "Developer"
    },
    {
      "user_id": 302,
      "username": "@backend_vlad",
      "full_name": "Влад Бэкендов",
      "role": "Developer"
    },
    {
      "user_id": 405,
      "username": "@devops_max",
      "full_name": "Максим Девопсов",
      "role": "DevOps"
    },
    {
      "user_id": 501,
      "username": "@qa_masha",
      "full_name": "Мария Тестировщикова",
      "role": "QA"
    }
  ],
  "messages": [
    {
      "user_id": 201,
      "username": "frontend_kirill",
      "full_name": "Кирилл Версталов",
      "text": "Я закончил перенос стора на Redux. Можно заливать на прод?",
      "timestamp": "2026-06-03T14:56:00+03:00"
    },
    {
      "user_id": 204,
      "username": "pm_ivan",
      "full_name": "Иван Менеджеров",
      "text": "Кайф, закрываю таску в жире. Дайте задачу девопсу, пусть разберётся с CI.",
      "timestamp": "2026-06-03T14:58:00+03:00"
    }
  ]
}
```

### Описание полей

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `event_id` | string | ✅ | Уникальный идентификатор батча |
| `occurred_at` | ISO-8601 datetime | ✅ | Время обработки батча (используется для расчёта дедлайнов) |
| `chat_id` | int | ✅ | ID Telegram-чата |
| `batch_start` | ISO-8601 datetime | ✅ | Начало временного окна |
| `batch_end` | ISO-8601 datetime | ✅ | Конец временного окна |
| `team` | `TeamMember[]` | ⚠️ опционально | Список участников команды. Если не передан — используется только `username` из логов чата |
| `messages` | `MessageDto[]` | ✅ | Массив сообщений из чата |

### Структура `TeamMember`

```json
{
  "user_id": 201,
  "username": "@frontend_kirill",
  "full_name": "Кирилл Версталов",
  "role": "Developer"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | int | Внутренний ID пользователя в системе ("святой" идентификатор) |
| `username` | string | Системный тег пользователя. Принимается как `@frontend_kirill`, так и `frontend_kirill` — LLM Worker добавит `@` сам |
| `full_name` | string | Полное имя. Используется для матчинга по неформальным именам и прозвищам ("Мишаня" → "Михаил Беккеров" → `@mikhail_be`) |
| `role` | string | Роль в команде: `PM`, `Developer`, `QA`, `Lead`, `DevOps`, и т.д. |

---

## Как LLM Worker использует `team`

LLM Worker вставляет список команды прямо в системный промпт LLaMA перед каждым батчем. Логика резолвинга `assignee` по приоритету:

1. **`@username` явно в чате** (`[10:00] @frontend_kirill: Беру`) → `@frontend_kirill`
2. **`username` в начале строки** (`[10:00] frontend_kirill: Ок, сделаю`) → `@frontend_kirill`
3. **Имя в тексте + матч по `full_name` в team** (`"Кирилл, займись"` при `full_name="Кирилл Версталов"`) → `@frontend_kirill`
4. **Прозвище/никнейм + матч по `full_name`** (`"Мишаня"` при `full_name="Михаил Беккеров"`) → `@mikhail_be`
5. **Роль в тексте + ОДИН человек с этой ролью в team** (`"пусть девопс"` при 1 DevOps) → `@devops_max`
6. **Роль в тексте + НЕСКОЛЬКО с этой ролью** (`"пусть фронт"` при 2 Developer) → `assignee: null` ⚠️
7. **Не найдено нигде** → `assignee: null`

> [!IMPORTANT]
> **Правило неоднозначности по роли**: если задача адресована роли (`"пусть бэк сделает"`), но людей с этой ролью несколько — мы создаём задачу с `assignee: null`. Бэкенд должен сам смаршрутизировать её. Задача **не теряется**.

---

## Выходные данные (LLM Worker → Spring)

LLM Worker пишет результаты в два топика:
- Новые задачи: `llm.tasks.create` (задаётся через `KAFKA_TOPIC_TASKS`)
- Смена статуса: `llm.tasks.status` (задаётся через `KAFKA_TOPIC_STATUS`)

> **Kafka key**: для обоих топиков `key = str(chat_id)`. Это сохраняет порядок событий из одного чата в одной партиции.

### 1. Создание задач (`llm.tasks.create`)

```json
{
  "chat_id": 1001,
  "source_batch_id": "unique-batch-12345",
  "title": "Разобраться с CI-пайплайном",
  "description": "«pm_ivan: Дайте задачу девопсу, пусть разберётся с CI»",
  "assignee": "@devops_max",
  "assignee_id": 405,
  "deadline": null,
  "priority": "MEDIUM"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `chat_id` | int | ID чата-источника |
| `source_batch_id` | string | `event_id` входящего батча для трассировки |
| `title` | string | Краткое название задачи. Формат: глагол + объект. Всегда на русском |
| `description` | string | Включает точную цитату из чата в формате `«author: text»` |
| `assignee` | string \| null | `@username` из team list или чат-лога. `null` если неоднозначно |
| `assignee_id` | int \| null | "Святой" `user_id` исполнителя, разрезолвленный из `team` массива |
| `deadline` | ISO-8601 \| null | Приведённый дедлайн. `null` если не указан |
| `priority` | `HIGH` \| `MEDIUM` \| `LOW` | Определяется по срочности и ключевым словам |

### 2. Смена статусов (`llm.tasks.status`)

```json
{
  "chat_id": 1001,
  "source_batch_id": "unique-batch-12345",
  "task_hint": "перенос стора на Redux",
  "assignee": "@frontend_kirill",
  "assignee_id": 201,
  "action": "COMPLETE"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `task_hint` | string | Краткое (2-5 слов) описание задачи, по которой меняется статус. Бэкенд матчит его к реальной задаче через fuzzy search |
| `assignee` | string \| null | Кто выполнил/принял/отменил задачу |
| `assignee_id` | int \| null | `user_id` исполнителя |
| `action` | `COMPLETE` \| `ASSIGN` \| `CANCEL` | Тип изменения |

---

## Как запустить локально

```bash
# MOCK — только структурная проверка, LLM не вызывается
uv run python -m tests.runner

# LIVE — реальный прогон через LLaMA (требует запущенного Ollama)
$env:LLM_TESTS="1"; uv run python -m tests.runner

# Отладка одного кейса
uv run python debug_run.py --file tests/cases/case-009-role-single-match.json --chain task
```
