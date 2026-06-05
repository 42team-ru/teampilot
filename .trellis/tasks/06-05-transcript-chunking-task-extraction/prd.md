# Transcript chunking + task/status extraction

## Goal

Транскрипция звонка (Whisper) может быть огромной (часовой звонок ≈ 15k+ слов).
Сейчас `process_transcript` отдаёт весь текст в LLM без ограничений — llama 3.1:8b (8k ctx) переполнится.

Нужно: нарезать транскрипт на чанки → на каждый чанк запустить classifier + task_chain + status_chain
(как `process_batch`, только входной текст — чанк транскрипта) → дедуп задач через Qdrant,
резолвинг статус-изменений через `find_task_by_hint`.

## Requirements

- Разбить текст транскрипта на чанки с overlap
  - `TRANSCRIPT_CHUNK_CHARS: int = 6000` (символов; ≈ 1500 токенов для русского)
  - `TRANSCRIPT_CHUNK_OVERLAP_CHARS: int = 500` (символов; перекрытие чтоб не терять контекст на границе)
- На каждый чанк:
  1. `classifier_chain` (дешёвая) — пропустить чанк если `confidence < CLASSIFIER_THRESHOLD`
  2. Если `has_task` → `task_chain` → дедуп через `is_task_duplicate(title, desc, team_id)` → `store_task` → publish `llm.tasks.create`
  3. Если `has_status_change` → `status_chain` → резолв через `find_task_by_hint(hint, team_id)` → publish `llm.status.change`
- `TranscriptReadyEvent` уже имеет `team_id` (добавлено в предыдущем таске)
- Новая функция: `llm/transcript.py` → `chunk_text(text, chunk_size, overlap) → list[str]`
- `process_transcript` в `main.py` переписывается через чанки

## Acceptance Criteria

- [ ] Транскрипт длиннее `TRANSCRIPT_CHUNK_CHARS` нарезается на ≥2 чанка
- [ ] Каждый чанк проходит через classifier, пустые чанки скипаются
- [ ] Задачи создаются, дедупликация через Qdrant работает (тест с повтором)
- [ ] Status changes с `resolved_task_id` (если есть похожая задача в Qdrant)
- [ ] Транскрипт длиной ≤ `TRANSCRIPT_CHUNK_CHARS` обрабатывается как один чанк (без overhead)

## Out of Scope

- Summarization перед экстракцией
- Team context (имена/роли) в транскриптах — нет данных, `team_context = "not provided"`
- Kanban columns в транскриптах — `column_id = null`

## Technical Notes

Файлы:
- `llm-worker/llm/transcript.py` — новый файл: `chunk_text()`
- `llm-worker/main.py` — переписать `process_transcript()`
- `llm-worker/settings.py` — добавить `TRANSCRIPT_CHUNK_CHARS`, `TRANSCRIPT_CHUNK_OVERLAP_CHARS`

Паттерн чанкинга:
```python
def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
```

`process_transcript` после рефакторинга ≈ `process_batch` но без proto/team/columns:
```
for chunk in chunk_text(text, ...):
    clf = classifier_chain(chunk)
    if clf.has_task:   task extraction + store + publish
    if clf.has_status: status extraction + find_task_by_hint + publish
```
