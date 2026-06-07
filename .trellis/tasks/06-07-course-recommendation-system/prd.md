# Course Recommendation System

## Goal

Система рекомендации курсов и обучающих материалов: менеджер добавляет курсы (Skillbox, Яндекс Практикум, Степик, YouTube, RuTube) в команду; Spring парсит og:title/og:description по URL; при просрочке дедлайна участнику автоматически отправляются релевантные курсы (через Qdrant + LLM Worker). Курсы бывают двух типов: командные (TEAM) и глобальные (GLOBAL). Глобальные засеяны в DataSeeder. Весь функционал реализован в боте.

---

## Decision Log

1. **Как менеджер добавляет курс** → **REST API**: `POST /teams/{teamId}/courses`
2. **Как выбираются курсы для рекомендации** → **LLM + Qdrant**: задача → `courses.recommend.request` Kafka → LLM Worker ищет в `QDRANT_COLLECTION_KNOWLEDGE` (`type="course"`) → `courses.recommend.result` → Spring → bots.notifications
3. **Кто делает поиск** → **LLM Worker через Kafka** (не Spring напрямую)
4. **Каталог курсов** → **Есть**: `GET /teams/{teamId}/courses` + бот для менеджера (добавление) и участника (просмотр)

---

## Requirements

### Spring (Java)

**Сущность `Course` (`courses` таблица):**
- `id` (UUID, AbstractEntity), `createdAt`, `updatedAt`
- `url` (String, nullable=false)
- `title` (String, nullable=false)
- `description` (TEXT, nullable)
- `thumbnailUrl` (String, nullable)
- `scope` (enum: TEAM / GLOBAL)
- `team` (ManyToOne → Team, nullable = true для GLOBAL)

**REST API — `CourseController` под `/courses`:**
- `POST /teams/{teamId}/courses` — менеджер добавляет курс; парсит og:title/og:description через jsoup; сохраняет; публикует `courses.indexed` Kafka-событие
- `GET /teams/{teamId}/courses` — возвращает курсы команды + все GLOBAL; доступно участникам

**DataSeeder — 15-20 глобальных курсов** (hardcoded title/description/url, без HTTP-запросов):
- Разнообразные: Python, Java, JavaScript, менеджмент, аналитика, ML, DevOps, дизайн, soft skills, базы данных, веб-разработка, Kotlin, Go, продуктовый менеджмент, Agile/Scrum
- Платформы: Skillbox, Яндекс Практикум, Степик, Coursera, YouTube
- Глобальные курсы публикуют `courses.indexed` с `teamId="GLOBAL"`

**Kafka-топики (новые):**
- `courses.indexed` — Spring → LLM Worker: `{courseId, title, description, teamId ("GLOBAL" или UUID), url}`
- `courses.recommend.request` — Spring → LLM Worker: `{requestId, taskId, taskTitle, taskDescription, teamId}`
- `courses.recommend.result` — LLM Worker → Spring: `{requestId, taskId, teamId, courseIds: [...]}`

**`NotificationScheduler` — новый метод `sendCourseRecommendations()`:**
- cron: каждые 30 минут
- Находит задачи: `localStatus=ACTIVE AND deadline < now AND courseRecommendedAt IS NULL`
- Для каждой публикует `courses.recommend.request`
- Устанавливает `courseRecommendedAt = now()` сразу (не ждёт ответа)
- Новое поле `courseRecommendedAt` (Instant) в `Task`

**`CourseRecommendConsumer`** — слушает `courses.recommend.result`:
- Получает `courseIds` → загружает из БД → публикует `BotNotificationEvent(type=COURSE_RECOMMENDATION)` с полем `courses: List<CourseInfo>` в `bots.notifications`

**`BotNotificationEvent`** — добавить:
- `type = "COURSE_RECOMMENDATION"`
- `courses: List<CourseInfo>` (courseId, title, url, description)

### LLM Worker (Python)

**`main.py`** — добавить consumer-поток для `courses.recommend.request`:
- Получает `{taskTitle, taskDescription, teamId}`
- Вызывает `search_knowledge(query=title+description, team_id=teamId, type="course", extra_team_ids=["GLOBAL"], limit=5)`
- Публикует `courses.recommend.result` с найденными `source_id` (= courseId)

**`infra/qdrant.py`** — расширить `search_knowledge`:
- Добавить `extra_team_ids: list[str] | None = None`
- Если задан — Qdrant `should` filter: `team_id IN (teamId, "GLOBAL")`

**Новый consumer для `courses.indexed`:**
- Получает событие → `store_knowledge(source_id=courseId, team_id=teamId, type="course", content=title+" "+description, title=title)`

### Bot (Python)

**`bot/handlers/courses.py`** — новый файл:
- **Менеджер — добавление курса:**
  - Entry: callback `courses:add:{teamId}`
  - FSM: `CoursesAddStates.waiting_for_url`
  - Принимает URL → POST `/courses/teams/{teamId}/courses` → показывает распознанный заголовок
- **Менеджер / участник — просмотр каталога:**
  - Entry: callback `courses:list:{teamId}`
  - GET `/teams/{teamId}/courses` → отображает список с пагинацией (по 5 курсов)
  - Каждый курс: title + короткое description + ссылка (InlineKeyboardButton url)

**`bot/services/course_service.py`** — новый файл:
- `add_course(team_id, url, telegram_id)` → POST к Spring
- `list_courses(team_id, telegram_id)` → GET к Spring

**`bot/kafka/consumer.py`** — добавить case `COURSE_RECOMMENDATION`:
```python
elif event.type == "COURSE_RECOMMENDATION":
    text = _format_course_recommendation(event)
    await self._send_to_recipients(...)
```

**Форматирование уведомления `COURSE_RECOMMENDATION`:**
```
📚 Задача просрочена: «<название задачи>»

Вот курсы, которые помогут в будущем:
1. <title> — <url>
2. <title> — <url>
...
```

**Добавить кнопки в меню менеджера (`team_ctx:manager:{teamId}`):**
- `📚 Курсы команды` → `courses:list:{teamId}`
- `➕ Добавить курс` → `courses:add:{teamId}`

**Добавить кнопку в меню участника:**
- `📚 Курсы команды` → `courses:list:{teamId}`

---

## Acceptance Criteria

- [ ] Менеджер может добавить курс через бота (URL → парсинг → сохранение)
- [ ] Добавленный курс появляется в каталоге команды
- [ ] Каталог доступен менеджеру и участнику через бота (пагинация)
- [ ] Глобальные курсы видны во всех командах
- [ ] DataSeeder содержит 15-20 разнообразных глобальных курсов
- [ ] При просрочке задачи участник получает рекомендацию через Telegram
- [ ] LLM Worker корректно ищет курсы по семантике задачи (team + GLOBAL)
- [ ] `courseRecommendedAt` проставляется, повторных рекомендаций нет

---

## Definition of Done

- Tests added/updated (unit/integration где уместно)
- Lint/typecheck/CI green
- DataSeeder содержит 15-20 глобальных курсов

---

## Out of Scope

- Редактирование/удаление курсов (только добавление в MVP)
- Аналитика прохождения курсов
- Рейтинги и отзывы на курсы
- Уведомления об истечении срока подписки на курс

---

## Technical Notes

**Spring — файлы для изменения:**
- `DataSeeder.java` — добавить 15-20 глобальных курсов
- `NotificationScheduler.java` — добавить `sendCourseRecommendations()`
- `BotNotificationEvent.java` — добавить `COURSE_RECOMMENDATION` + `courses` поле
- `NotificationEventPublisher.java` — добавить `publishCourseRecommendation()`
- `Task.java` — добавить поле `courseRecommendedAt`
- `KafkaTopics` — добавить `COURSES_INDEXED`, `COURSES_RECOMMEND_REQUEST`, `COURSES_RECOMMEND_RESULT`
- `build.gradle` — добавить `implementation 'org.jsoup:jsoup:1.17.2'`

**Spring — новые файлы:**
- `entity/Course.java` + `entity/enums/CourseScope.java`
- `repository/CourseRepository.java`
- `service/CourseService.java` — add + list + URL parsing
- `rest/CourseController.java`
- `event/CourseIndexedEvent.java`, `event/CourseRecommendRequestEvent.java`, `event/CourseRecommendResultEvent.java`
- `service/CourseEventPublisher.java`
- `kafka/CourseRecommendConsumer.java`

**LLM Worker — файлы для изменения:**
- `infra/qdrant.py` — расширить `search_knowledge` с `extra_team_ids`
- `main.py` — добавить 2 новых consumer-потока (`courses.indexed`, `courses.recommend.request`)
- `models.py` — добавить `CourseIndexedEvent`, `CourseRecommendRequestEvent`, `CourseRecommendResultEvent`

**Bot — файлы для изменения:**
- `kafka/consumer.py` — case `COURSE_RECOMMENDATION`
- `models/events.py` — добавить `courses` поле в `BotNotificationEvent`
- Меню менеджера / участника — добавить кнопки курсов
- `kafka/topics.py` — топики курсов (если нужно)

**Bot — новые файлы:**
- `handlers/courses.py`
- `services/course_service.py`
- `states/courses.py`

**Паттерн парсинга URL (jsoup):**
```java
Document doc = Jsoup.connect(url).timeout(5000).get();
String title = doc.select("meta[property=og:title]").attr("content");
String description = doc.select("meta[property=og:description]").attr("content");
```

**Qdrant GLOBAL поиск — расширение `search_knowledge`:**
```python
# Qdrant should filter: (team_id == teamId) OR (team_id == "GLOBAL")
must = []  # убрать team_id из must
should = [
    FieldCondition(key="team_id", match=MatchValue(value=team_id)),
    FieldCondition(key="team_id", match=MatchValue(value="GLOBAL")),
]
filter = Filter(should=should)
```
