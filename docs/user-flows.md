# TeamPilot — User Flows

Activity-диаграммы для всех ключевых пользовательских сценариев.
Sequence-диаграммы с деталями системного взаимодействия — в [README.md](../README.md).

---

## Содержание

1. [Онбординг — регистрация и создание команды](#1-онбординг)
2. [Чат → Задачи в YouGile](#2-чат--задачи)
3. [Chrome Extension — реалтайм-встреча](#3-chrome-extension--встреча)
4. [Вечерний синк](#4-вечерний-синк)
5. [Аудио-встреча через бота](#5-аудио-встреча)
6. [Управление задачами](#6-управление-задачами)
7. [Дедлайн-уведомления и стейл-алерты](#7-уведомления)
8. [Геймификация и профиль](#8-геймификация)
9. [Рекомендации курсов](#9-рекомендации-курсов)
10. [База знаний (`/wiki`)](#10-база-знаний)

---

## 1. Онбординг

Регистрация пользователя, создание или вступление в команду, привязка YouGile.

```mermaid
flowchart TB
    Start(["Пользователь"]) --> A["/start в Telegram-боте"]
    A --> B{"Уже\nзарегистрирован?"}
    B -- Да --> Menu(["Главное меню"])
    D{"Роль"} -- Менеджер --> E["Ввести название команды"]
    E --> F["Команда создана\nРоль: MANAGER"]
    F --> G{"Привязать YouGile\nпрямо сейчас?"}
    G -- Да --> H["/link"]
    H --> I["Ввести YouGile API key\nи board ID"]
    I --> J{"API key\nвалиден?"}
    J -- Нет --> K["Ошибка — повторить"]
    K --> I
    J -- Да --> L["YouGile привязан ✅\nКолонки загружены"]
    L --> M["Менеджер генерирует\nинвайт-ссылку /invite"] & Menu
    M --> N["Отправляет ссылку\nучастникам команды"]
    G -- Позже --> Menu
    D -- Участник --> O["Ввести инвайт-код или перейти по ссылке"]
    O --> P{"Код\nвалиден?"}
    P -- Нет --> Q["Ошибка — повторить"]
    Q --> O
    P -- Да --> R["Добавлен в команду\nРоль: MEMBER"]
    R --> Menu
    N -. Участник переходит .-> O
    B -- Нет --> D
```

---

## 2. Чат → Задачи

Автоматическое извлечение задач из переписки в Telegram-чате команды.

```mermaid
flowchart TD
    Start([Участник или менеджер]) --> A["Пишет сообщение\nв Telegram-чат команды"]
    A --> B["Бот накапливает сообщения"]
    B --> C{"Батч готов?\n≥ 3 сообщений\nили 5 мин прошло"}
    C -->|Нет| B
    C -->|Да| D["Kafka: messages.batches\n(Protobuf)"]

    D --> E["LLM Worker\nдешёвый классификатор"]
    E --> F{Есть ли задача\nв батче?}
    F -->|Нет| G["Пропустить батч"]
    F -->|Да| H["LLM Worker\nдорогая модель\nextract title, assignee, deadline"]

    H --> I["Qdrant: проверить семантический дубликат"]
    I --> J{Дубликат?}
    J -->|Да| K["Пропустить"]
    J -->|Нет| L{Confidence\n≥ 0.90?}

    L -->|Да — auto-confirm| M["Spring: создать задачу\nстатус CONFIRMED\nYouGile сразу"]
    L -->|Нет| N["Kafka: llm.tasks.create\nSpring: задача PENDING"]
    N --> O["Бот: сообщение в чат\nс кнопками"]
    O --> P([Менеджер])
    P --> Q{"Нажимает кнопку"}
    Q -->|"✅ Подтвердить"| R["Задача CONFIRMED\nYouGile создана"]
    Q -->|"✏️ Изменить"| S["Бот: форма редактирования\ntitle / assignee / deadline"]
    S --> R
    Q -->|"❌ Отклонить"| T["Задача CANCELLED\nQdrant: удалить"]
    M --> R
```

---

## 3. Chrome Extension — Встреча

Запись и транскрипция встречи в браузере с real-time созданием задач.

```mermaid
flowchart TD
    Start([Пользователь]) --> A["Открывает popup\nChrome Extension"]
    A --> B{Авторизован?}

    B -->|Нет| C["Нажать Login"]
    C --> D["Бэкенд: POST /auth/extension-login\nВозвращает 6-значный код"]
    D --> E["Popup показывает код"]
    E --> F["Пользователь отправляет\n/start КОД в Telegram-бот"]
    F --> G["Бот подтверждает сессию\nна бэкенде"]
    G --> H["Extension опрашивает\nGET /auth/extension-login/{код}"]
    H --> I{Подтверждено?}
    I -->|Нет — ждёт| H
    I -->|Да| J["JWT сохранён\nв chrome.storage.local ✅"]
    B -->|Да| J

    J --> K["Открыть нужную вкладку\nвстреча, звонок, конференция"]
    K --> L["Нажать Record в popup"]
    L --> M["Spring: GET /meetings/by-url\nили POST /meetings создать встречу"]
    M --> N["STOMP подключение\nAuthorization: Bearer token"]
    N --> O["Подписка на\n/topic/meetings/{id}/results"]
    O --> P["chrome.tabCapture + getUserMedia\nзахват вкладки и микрофона"]
    P --> Q["AudioContext: микс\nвкладка + микрофон"]

    Q --> R["Цикл каждые 30 сек"]
    R --> S["MediaRecorder → WebM blob\nfixWebmDuration"]
    S --> T["STOMP SEND\n/app/meetings/{id}/chunks\naudioBase64, chunkIndex"]
    T --> U["Spring → MinIO\nmeetings/{id}/chunks/{N:06d}"]
    U --> V["Kafka: meetings.audio.chunks"]
    V --> W["LLM Worker: Whisper\nтранскрипция чанка"]
    W --> X["Накопление контекста\nклассификатор → задачи"]
    X --> Y["Qdrant hints\nscore ≥ 0.80"]
    Y --> Z["Kafka: meetings.live.result"]
    Z --> AA["STOMP broadcast\n/topic/meetings/{id}/results"]
    AA --> AB["Sidepanel обновляется\nтранскрипция + подсказки"]
    AB --> AC{Продолжить\nзапись?}
    AC -->|Да| R
    AC -->|Нет — Stop| AD["Финальный чанк\nfinalChunk=true\n250 мс"]

    AD --> AE["LLM Worker: финализация"]
    AE --> AF["Скачать все чанки MinIO\nобъединить merge_audio_chunks"]
    AF --> AG["Whisper: полная\nтранскрипция встречи"]
    AG --> AH["LLM: title, description,\nsummary встречи"]
    AH --> AI["Qdrant: store_knowledge\ntype=meeting_summary"]
    AI --> AJ["Повторное извлечение задач\nиз полного транскрипта"]
    AJ --> AK["STOMP: финальный результат\nfinalResult=true"]
    AK --> AL["Sidepanel: итог встречи\nзадачи + резюме"]
    AL --> AM([Менеджер подтверждает задачи])
```

---

## 4. Вечерний синк

Ежедневный статус-чек команды в 18:00, автоматическое закрытие задач.

```mermaid
flowchart TB
    Sched(["EveningSyncScheduler (ежедневный крон в 18:00)"]) --> A["startSyncForAllTeams\nфильтр: исключить MANAGER\nи excused пользователей"]
    A --> B["SyncStateService: openSession\nKafka: bots.notifications\ntype=SYNC_PROMPT"]
    B --> C@{ label: "Бот: сообщение в чат\\n'Вечерний синк — что сделал сегодня?'" }
    C --> D(["Участник команды"])
    D --> E{"Реакция\nдо 19:00"} & S{"Участник\nвыбирает"}
    E -- /excuse --> F["Отмечен как excused\nисключён из итогов синка"]
    E -- Написал отчёт --> G["POST /sync/submit\ntekst в свободной форме"]
    E -- Нет ответа --> H["Отмечен как not_responded"]
    G --> I["Spring: загрузить активные задачи\nKafka: sync.requests"]
    I --> J["LLM Worker\nQdrant: поиск по тексту\nlimit=10, score ≥ STATUS_HINT_THRESHOLD"]
    J --> K{"Совпадения\nнайдены?"}
    K -- Нет — fallback --> L["LLM: sync_match_chain\nJSON-список активных задач"]
    K -- Да --> M["SyncDraftItem\nTask matched, is_new_task=false"]
    L --> N{"LLM\nнашёл?"}
    N -- Нет --> O["SyncDraftItem\nis_new_task=true\nновая задача"]
    N -- Да --> M
    O --> M
    M --> P["Kafka: sync.draft"]
    P --> Q["Spring: обогатить assignee\nKafka: bots.notifications\ntype=SYNC_DRAFT"]
    Q --> R["Бот: ЛС участнику\nчерновик с кнопками ✅ ✏️ ❌"]
    R --> D
    S -- ✅ Подтвердить всё --> T["confirmAll\nЗадачи CONFIRMED\nYouGile: переместить карточки"]
    S -- ✏️ Редактировать --> U["Изменить черновик\nи подтвердить"]
    U --> T
    S -- ❌ Отклонить --> V["Новые задачи → proposalCache\nМенеджер получает уведомление"]
    F --> Close(["EveningSyncScheduler\ncron 0 0 19 * * *"])
    H --> Close
    T --> Close
    V --> Close
    Close --> W["closeSyncAndSendSummary"]
    W --> X["Итоговый отчёт менеджерам:\n✅ responded / ❌ notResponded / 💤 excused"] & Y["Очистить сессии"]

    C@{ shape: rect}
```

---

## 5. Аудио-встреча

Загрузка записи встречи через Telegram-бота для автоматической транскрипции.

```mermaid
flowchart TB
    Start(["Менеджер"]) --> A{"Тип загрузки"}
    A -- Голосовое\nсообщение --> B["Записать voice message\nв Telegram-чате"]
    A -- Файл\nMP3 / OGG / WAV / WebM --> C["Загрузить аудиофайл\nчерез бота"]
    B --> D["Бот: выбрать команду\nинлайн-кнопки"]
    C --> D
    D --> E{"Команда\nвыбрана"}
    E --> F["Spring: MinIO upload\naudio/{teamId}/{fileId}"]
    F --> G["Kafka: audio.new\n{teamId, minioKey, fileId}"]
    G --> H["LLM Worker скачать файл из MinIO"]
    H --> I["Конвертация в WAV\n(ffmpeg)"]
    I --> J["faster-whisper\nтранскрипция → текст"]
    J --> K["Чанкинг транскрипта\nс перекрытием (overlap)"]
    K --> L["Для каждого чанка:\nLLM classifier → task chain"]
    L --> M["Qdrant: дедупликация\nпо семантике"]
    M --> N{"Дубликат?"}
    N -- Да --> O["Пропустить"]
    N -- Нет --> P["Kafka: llm.tasks.create"]
    P --> Q["Spring: задача PENDING"]
    Q --> R["Бот: сообщение в чат\nс кнопками ✅ ✏️ ❌"]
    R --> S(["Менеджер подтверждает"])
    O --> T{"Ещё чанки?"}
    S --> T
    T -- Да --> K
    T -- Нет --> U["Готово: все задачи обработаны"]
```

---

## 6. Управление задачами

Просмотр, фильтрация и обновление задач через Telegram-бота.

```mermaid
flowchart TD
    Start([Пользователь]) --> A["/tasks"]
    A --> B["Бот: список задач команды\nвсе колонки YouGile"]

    B --> C{Фильтровать\nпо колонке?}
    C -->|Да| D["Кнопки с названиями\nколонок YouGile\n(динамически)"]
    D --> E["Выбрать колонку\nнапр. In Progress"]
    E --> F["Отфильтрованный список\nтолько выбранная колонка"]
    C -->|Нет| G["Полный список"]

    F --> H{Действие\nс задачей}
    G --> H

    H -->|Открыть детали| I["Название, исполнитель\nдедлайн, статус, описание"]
    I --> H

    H -->|Сменить статус| J{Роль\nпользователя}
    J -->|Менеджер| K["Выбрать любой\nстатус / колонку"]
    J -->|Участник| L["Только свои задачи\nдвижение → Done"]
    K --> M["Spring: PATCH /tasks/{id}/status"]
    L --> M
    M --> N["YouGile API: переместить\nкарточку retry backoff 3x"]
    N --> O["Kafka: tasks.lifecycle\ntype=UPDATED"]
    O --> P["Qdrant: обновить task_archive"]
    O --> Q["XP начислено ✨"]

    H -->|"Назначить\n(только Менеджер)"| R{Менеджер?}
    R -->|Нет| S["Доступ запрещён"]
    R -->|Да| T["Выбрать участника\nиз команды"]
    T --> M

    H -->|Вернуться| B
```

---

## 7. Уведомления

Автоматические алерты о дедлайнах и застрявших задачах.

```mermaid
flowchart TD
    Sched(["NotificationScheduler\nкаждые 30 мин"]) --> A["Проверить все активные задачи"]

    A --> B{Дедлайн\nчерез ≤ 2 ч?}
    B -->|Да| C["Kafka: bots.notifications\ntype=DEADLINE_ALERT"]
    C --> D["Бот: ЛС исполнителю\n⚠️ Дедлайн через 2 часа\nназвание задачи"]

    A --> E{Задача не обновлялась\n≥ 24 ч?}
    E -->|Да| F["Kafka: bots.notifications\ntype=STALE_TASK"]
    F --> G["Бот: ЛС исполнителю\n🕒 Задача зависла\nназвание задачи"]

    D --> H([Исполнитель])
    G --> H

    H --> I{Реакция}
    I -->|"/tasks → сменить статус"| J["Задача обновлена\nалерт не повторится"]
    I -->|Игнорировать| K["При следующей проверке алерт повторится"]

    A --> L{Несколько задач для одного чата?}
    L -->|Да| M["Батчинг уведомлений\nодно сообщение на чат"]
    M --> D
    L -->|Нет| D
```

---

## 8. Геймификация

Начисление XP, уровни, достижения и просмотр RPG-профиля.

```mermaid
flowchart TD
    Start([Пользователь]) --> A{Событие}

    A -->|"Задача confirmed"| B["+ XP за выполнение\nбазовые очки"]
    A -->|"Выполнено до дедлайна"| C["+ XP бонус\nза своевременность"]
    A -->|"Серия выполненных задач"| D["+ XP streak-бонус"]

    B --> E["Spring: обновить\nXP пользователя в БД"]
    C --> E
    D --> E

    E --> F{Достигнут\nновый уровень?}
    F -->|Да| G["Бот: 🎉 Level Up!\nновый ранг и título"]
    F -->|Нет| H["Обновить прогресс-бар"]
    G --> H

    E --> I{Выполнено\nусловие ачивки?}
    I -->|Да| J["Бот: 🏆 Новое достижение!\nназвание и описание"]
    I -->|Нет| H
    J --> H

    H --> K([Пользователь])
    K --> L["/profile"]
    L --> M["Бот: RPG-карточка профиля\nИмя, ранг, уровень\nXP / XP до следующего\nЗначки достижений\nМесто в рейтинге команды"]
    M --> K
```

---

## 9. Рекомендации курсов

Менеджер добавляет курсы, система автоматически рекомендует их при просроченных задачах.

```mermaid
flowchart TD
    subgraph "Добавление курса (Менеджер)"
        MA([Менеджер]) --> A["POST /teams/{id}/courses\nURL курса"]
        A --> B["Spring: jsoup → og:title\nog:description, og:image"]
        B --> C{Парсинг\nуспешен?}
        C -->|Нет| D["Ошибка — ввести вручную\ntitle + description"]
        D --> E["Курс сохранён\nscope = TEAM или GLOBAL"]
        C -->|Да| E
        E --> F["Kafka: courses.indexed\n{courseId, teamId, title, description}"]
        F --> G["LLM Worker: store_knowledge\ntype=course, Qdrant"]
        G --> H["Курс готов к рекомендациям ✅"]
    end

    subgraph "Автоматическая рекомендация"
        Sched(["NotificationScheduler\nкаждые 30 мин"]) --> I["Задачи с истёкшим дедлайном\nbez courseRecommendedAt"]
        I --> J["Kafka: courses.recommend.request\ntaskTitle + taskDescription"]
        J --> K["LLM Worker: semantic search\nQdrant team_knowledge\ntype=course\nteam + GLOBAL каталог, limit=5"]
        K --> L{Курсы\nнайдены?}
        L -->|Нет| M["Нет рекомендаций"]
        L -->|Да| N["Kafka: courses.recommend.result\ntop-5 course_ids"]
        N --> O["Spring: courseRecommendedAt = now\nбот: ЛС исполнителю"]
        O --> P([Исполнитель])
        P --> Q["📚 Подборка курсов\nпо теме просроченной задачи"]
        Q --> R{Действие}
        R -->|Открыть| S["Ссылка на ресурс\nSkillbox / Stepik / YouTube / etc."]
        R -->|Игнорировать| T["Повтор не предусмотрен\ncourseRecommendedAt установлен"]
    end
```

---

## 10. База знаний

Автоматическое накопление знаний команды и ответы на вопросы через `/wiki`.

```mermaid
flowchart TD
    subgraph "Запрос знаний (/wiki)"
        Start([Пользователь]) --> A["/wiki вопрос в свободной форме"]
        A --> B["Spring: передать в LLM Worker\nPOST /knowledge/ask\n{teamId, question}"]
        B --> C["Qdrant: semantic search\nколлекция team_knowledge\nвсе типы записей"]
        C --> D{Результаты\nнайдены?}
        D -->|Да| E["LLM: сформировать ответ\nна основе чанков"]
        D -->|Нет| F["Ответ: данных нет\nв базе знаний команды"]
        E --> G["Бот: ответ + источники\n(тип: встреча / файл / задача / курс)"]
        F --> G
        G --> Start
    end

    subgraph "Автоматическое пополнение"
        H{Источник} -->|"Файл загружен\nв команду"| I["Spring: файл → MinIO\nKafka: files.new"]
        H -->|"Встреча завершена\n(finalChunk=true)"| J["LLM: summary встречи\ntitle + description"]
        H -->|"Задача CONFIRMED\nили UPDATED"| K["Kafka: tasks.lifecycle"]

        I --> L["LLM Worker:\nfile_summary chain\nчанкование текста"]
        J --> M["store_knowledge\ntype=meeting_summary"]
        K --> N["store_knowledge\ntype=task_archive\ntitle + description"]

        L --> O["store_knowledge\ntype=file_summary"]
        M --> P[("Qdrant\nteam_knowledge")]
        N --> P
        O --> P
    end
```
