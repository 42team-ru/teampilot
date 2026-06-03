# Digital Penetration — AI PM Bot

## О проекте

Хакатон-проект: бот-ассистент в роли project-менеджера. Читает Telegram-чат → извлекает задачи → ведёт канбан
(YouGile) → напоминает о дедлайнах.

**Целевая аудитория:** IT-команды, менеджеры, госорганы.

---

## Архитектура

```
Telegram Bot (Python)
  ├─ батчи сообщений ──────────────► Kafka: messages.raw
  ├─ /start, /link ────────────────► REST: /start, /link
  ├─ аудио встречи ────────────────► MinIO → Kafka: audio.new
  └─ подтверждение задач ◄──────── Kafka: bots.tasks

Spring Monolith (Java)
  ├─ читает messages.raw ──────────► сохраняет батчи → отдаёт LLM-воркеру
  ├─ читает llm.tasks.create ──────► создаёт задачу → YouGile API
  ├─ читает llm.status.change ─────► меняет статус задачи
  ├─ читает audio.new ─────────────► Whisper → расшифровка → LLM → задачи
  ├─ cron-планировщик ─────────────► Kafka: bots.notifications
  └─ YouGile синхронизация

LLM Worker (Python)
  ├─ читает batches ───────────────► дешёвая LLM: есть ли задача?
  │                                  дорогая LLM: создать задачу
  └─ пушит ────────────────────────► Kafka: llm.tasks.create / llm.status.change
```

### Kafka-топики

| Топик                | Направление  | Описание                               |
|----------------------|--------------|----------------------------------------|
| `messages.raw`       | Bot → Spring | Батчи сообщений из чата                |
| `users.events`       | Bot → Spring | Регистрация пользователя               |
| `audio.new`          | Bot → Spring | Новое аудио в MinIO                    |
| `llm.tasks.create`   | LLM → Spring | Создать задачу                         |
| `llm.status.change`  | LLM → Spring | Сменить статус / назначить             |
| `bots.tasks`         | Spring → Bot | Подтверждение задачи (кнопки ✅/✏️/❌) |
| `bots.notifications` | Spring → Bot | Дедлайн-алерты, вечерний дайджест      |

---

## Структура репозитория

```
backend/
  monolith/              — основной Spring-сервис (Spring Boot 3)
  core/
    web-common/          — ErrorResponse, GlobalExceptionHandler, ResponseUtils, PageResponse
    common-data/         — AbstractEntity (UUID, createdAt, updatedAt), JPA config
    kafka-common/        — KafkaSender, AbstractEventPublisher, BaseEvent, KafkaTopics
    security-common/     — UserPrincipal
    logging-common/      — structured logging (MDC, traceId)
    s3-common/           — S3/MinIO: S3Service, AbstractStoredFileEntity
infrastructure/
  docker/                — docker-compose.core / .observability / .services / .seed
  config/                — Grafana, Loki, Tempo, Prometheus, Alloy, Redpanda Console
  database/              — SQL-миграции (001_CREATE_AUTH.sql)
```

---

## Dev-команды

```bash
make core-up        # PostgreSQL + Kafka (Redpanda) + MinIO
make dev-up         # core + services
make obs-up         # Grafana + Loki + Tempo + Prometheus
make staging-up     # всё: core + obs + services
make core-down      # остановить core
make clean          # удалить все контейнеры и volumes

make build          # jibDockerBuild (локально)
make push           # запушить образы в ghcr.io/42team-ru
make release        # build + push (jib)

make seed           # заполнить БД тестовыми данными
make ps             # статус контейнеров
```

---

## Соглашения по коду

### Соглашения по Spring
Не добавляй в RequestMapping /api. Пиши /auth, /user, /tasks. Не пиши /api/users, /api/tasks
Не пиши Flyway миграции. Все работает через ddl-auto: update.

### Исключения — только через AppException

Не кидать `RuntimeException`, `ResponseStatusException`, `IllegalArgumentException` напрямую.
`GlobalExceptionHandler` обрабатывает `AppException` и возвращает структурированный `ErrorResponse`.

```java
throw AppException.notFound("Task %s not found".formatted(id));
throw AppException.alreadyExists("Username already taken");
throw AppException.forbidden("You don't own this task");
throw AppException.unauthorized("Token expired");
throw AppException.badRequest("Invalid date range");
throw AppException.internalError("YouGile API unavailable");
// с причиной (для логирования стектрейса):
```

### Ответы контроллеров

```java
// 201 Created
return ResponseUtils.created("/api/tasks/"+saved.getId(),dto);
return ResponseUtils.page(PageResponse.fromPage(page));
return ResponseUtils.ok(dto);
return ResponseUtils.noContent();
```

### Сущности — наследуй AbstractEntity

```java

@Entity
public class Task extends AbstractEntity {
}
// AbstractEntity даёт: UUID id, Instant createdAt, Instant updatedAt
```

### Kafka — наследуй BaseEvent

```java
public record TaskCreatedEvent(String taskId, String title, String assignee, Instant deadline)
        implements BaseEvent { ...
}
```

Публикация через `AbstractEventPublisher`:

```java

@Component
public class TaskEventPublisher extends AbstractEventPublisher {
    public void publishTaskCreated(Task task) {
        send(KafkaTopics.TASKS_CREATED, new TaskCreatedEvent(...));
    }
}
```

### S3/MinIO — через S3Service

```java
s3Service.upload(bucket, key, inputStream, contentType);

String presignedUrl = s3Service.presignedGetUrl(bucket, key, Duration.ofMinutes(15));
```

---

## Технологический стек

| Слой             | Технология                                  |
|------------------|---------------------------------------------|
| Backend          | Java 21, Spring Boot 3, Gradle 9            |
| БД               | PostgreSQL + Flyway-миграции                |
| Очередь          | Redpanda (Kafka-совместимый)                |
| Хранилище файлов | MinIO (S3-совместимый)                      |
| Контейнеризация  | Docker Compose + Jib                        |
| Observability    | Grafana + Loki + Tempo + Prometheus + Alloy |
| Reverse proxy    | Caddy                                       |
| Bot              | Python + Telegram Bot API                   |
| ASR              | Whisper (Ollama локально)                   |
| Kanban           | YouGile API                                 |
