# PRD: Meeting Bot — Voice Q&A Agent

## Цель

Голосовой агент на базе wake word + LLM с tool calling. Участник звонка говорит "ПИЛОТ, ..." — бот отвечает голосом в течение 10-15 секунд, используя данные из Spring backend и Qdrant.

Зависит от: `06-11-telemost-playwright-bot-passive-listener` (бот уже в звонке).

---

## User Flow

```
Участник: "ПИЛОТ, сколько задач сейчас в беклоге?"
  → [~0ms]   Wake word детектор слышит "ПИЛОТ"
  → [0-5s]   Запись вопроса до тишины (VAD)
  → [+0.2s]  Upload WAV в MinIO
  → [+0.1s]  Kafka: voice.query {minio_key, correlation_id, meeting_id}
  → [+0.2s]  Groq Whisper → "сколько задач сейчас в беклоге?"
  → [+1.5s]  LLM Worker: tool call → GET /tasks/stats
  → [+0.5s]  LLM формулирует: "В беклоге сейчас 8 задач, из них 2 просрочены"
  → [+0.1s]  Kafka: voice.response {correlation_id, text}
  → [+0.4s]  edge-tts → WAV
  → [+0.1s]  Воспроизведение через virtual mic → все в звонке слышат
Итого: ~3-8 секунд после окончания вопроса
```

---

## Wake Word

- Библиотека: **OpenWakeWord**
- Слово: "pilot" (английское произношение) для MVP — OpenWakeWord предобучен
- В будущем: кастомная модель на "ПИЛОТ" (20-30 записей + `train_custom_verifier.py`)
- Работает непрерывно в отдельном потоке, не мешает записи аудио для транскрипции

---

## Архитектура

```
audio_pipeline.py (постоянно работает)
  ├─ wake_word_detector (OpenWakeWord) — слушает непрерывно
  │     ↓ trigger
  └─ question_recorder (webrtcvad) — пишет до 1.5 сек тишины
        ↓ WAV
  minio_uploader → Kafka: voice.query {correlation_id, minio_key, meeting_id}

LLM Worker (новая ветка)
  voice.query event:
    → Groq Whisper (транскрипция)
    → LLM (claude-haiku / gpt-4o-mini) с tools:
        • get_task_stats() → GET /tasks/stats
        • search_tasks(query) → Qdrant
        • create_task(title, assignee) → POST /tasks
        • get_meeting_summary() → Qdrant (эмбеддинги текущего транскрипта)
    → Kafka: voice.response {correlation_id, text}

Bot (consumer)
  voice.response → edge-tts → sounddevice.play() через virtual mic
```

---

## Новые Kafka топики

| Топик | Направление | Поля |
|---|---|---|
| `voice.query` | Bot → LLM Worker | `correlation_id, minio_key, meeting_id, team_id` |
| `voice.response` | LLM Worker → Bot | `correlation_id, text` |

---

## Tools для LLM Worker

```python
tools = [
    {
        "name": "get_task_stats",
        "description": "Счётчики задач команды: беклог, в работе, просроченные, завершённые",
        # GET /tasks/stats?teamId=...
    },
    {
        "name": "search_tasks", 
        "description": "Семантический поиск по задачам и транскриптам встреч",
        "parameters": {"query": "string"}
        # Qdrant
    },
    {
        "name": "create_task",
        "description": "Создать задачу и назначить на участника",
        "parameters": {"title": "string", "assignee_name": "string", "description": "string"}
        # POST /tasks
    },
    {
        "name": "get_meeting_summary",
        "description": "Краткий итог текущей встречи по накопленным транскриптам",
        # Qdrant: поиск по meeting_id за сегодня + LLM summarize
    }
]
```

---

## TTS

- **edge-tts**, голос `ru-RU-DmitryNeural`
- Генерация: ~300-500ms для фразы до 30 слов
- Воспроизведение через PulseAudio virtual source (тот же, что настроен в Task 1)

---

## Параллельная работа двух режимов

```
audio_pipeline.py
  ├─ Thread A: continuous wake word detection
  ├─ Thread B: 30-sec passive recording → audio.new (Task 1)
  └─ Thread C: question recording (активен только после wake word)
```

Thread C прерывает Thread B на время записи вопроса (или пишет в отдельный буфер — не смешивать с passive чанками).

---

## Scope MVP

- [ ] OpenWakeWord интеграция (слово "pilot")
- [ ] webrtcvad для детекции конца речи
- [ ] Kafka: voice.query / voice.response топики
- [ ] LLM Worker: новая ветка VOICE_QUERY с 4 tools
- [ ] Spring: GET /tasks/stats endpoint
- [ ] edge-tts → воспроизведение через virtual mic
- [ ] Корреляция запрос/ответ по correlation_id

## Latency бюджет (цель: ≤ 15 сек)

| Этап | Бюджет |
|---|---|
| Запись вопроса | 2-5 сек (зависит от пользователя) |
| Upload + Kafka | 0.3 сек |
| Groq Whisper | 0.2 сек |
| LLM + 1 tool call | 2 сек |
| edge-TTS | 0.5 сек |
| **Итого после конца фразы** | **~3 сек** |

## Стек
- Python: openwakeword, webrtcvad, edge-tts, sounddevice
- LLM: claude-haiku-4-5 или gpt-4o-mini (tool calling)
- STT: Groq Whisper (уже используется)
- Vector: Qdrant (уже в стеке)
