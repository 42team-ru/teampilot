# YouGile Retry on All Requests

## Goal

Все HTTP-вызовы к YouGile API падают при сетевых сбоях (таймаут, 5xx) без повторных попыток. Задача: добавить retry-механизм на каждый запрос к YouGile, чтобы временные сетевые ошибки не приводили к потере данных (например, задача создаётся в БД с PENDING_SYNC, но не попадает в YouGile).

## Requirements

* Retry при `IOException`, таймаутах и 5xx-ответах от YouGile
* Exponential backoff между попытками (не долбить сервер подряд)
* Ограниченное число попыток (не уходить в бесконечный цикл)
* Покрывает все методы `YouGileService`: `createTask`, `updateTask`, `deleteTask`, `fetchTask`, `fetchAllTasksForBoard`, `fetchStickers`, `fetchColumns`
* Ошибка после всех попыток → логируется, не бросается дальше (существующее поведение)

## Acceptance Criteria

* [ ] При первом вызове таймаут/5xx → делается ещё N попыток с backoff
* [ ] После N неудачных попыток — логируется `ERROR`, возвращается `Optional.empty()` / пустой список
* [ ] Успешный retry после первой ошибки — задача создаётся в YouGile
* [ ] Нет новых зависимостей в build.gradle (используем Reactor retry, уже в classpath)

## Decision (ADR-lite)

**Context**: YouGile API вызовы падают при сетевых сбоях без повторных попыток  
**Decision**: 3 попытки, exponential backoff 2s → 4s → 8s (Reactor `Retry.backoff`)  
**Consequences**: суммарно ~75s при полной недоступности; без новых зависимостей

## Technical Approach (предварительно)

Все вызовы к YouGile API — через сгенерированный `DefaultApi`, который возвращает `Mono<T>`. В `YouGileService` везде вызывается `.block()`.

**Подход: Reactor retry wrapper**

Добавить приватный helper:
```java
private <T> T blockWithRetry(Mono<T> mono) {
    return mono
        .retryWhen(Retry.backoff(maxAttempts, firstBackoff).filter(this::isRetryable))
        .block();
}
```

Заменить все `.block()` на `blockWithRetry(...)`. Никаких новых зависимостей.

## Technical Notes

* Spring Boot 4.0.3, WebFlux в classpath → `reactor.util.retry.Retry` доступен
* `YouGileService.java` — единственное место с API-вызовами
* `YougileClientConfig` — создаёт `ApiClient` / `DefaultApi`
* `TaskRepository.findBySyncStatus()` уже есть — для будущего retry-шедулера (out of scope)
* Таймаут текущий: 30 секунд (из лога: `connection timed out after 30000 ms`)

## Out of Scope

* Ретрай-шедулер для PENDING_SYNC задач в БД (отдельная задача)
* Изменение таймаута WebClient
* Circuit breaker / Resilience4j
