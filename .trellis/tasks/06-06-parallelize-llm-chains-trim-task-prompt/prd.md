# parallelize-llm-chains-trim-task-prompt

## Goal

Ускорить обработку батча после классификации: сейчас task_chain и status_chain вызываются последовательно, хотя они независимы. Также убрать избыточные few-shot примеры из task prompt — они напрямую влияют на latency (больше токенов = дольше).

## What I already know

* `process_batch` в `processor.py`: сначала `_extract_tasks`, потом `_extract_statuses` — строго последовательно
* Обе функции полностью независимы (разные входы, разные цепочки, разные выходы)
* `TASK_SYSTEM` в `llm/prompts.py` — 9 few-shot примеров, из которых два дублируют паттерны других:
  - Пример 3 (строки 253-269): "Qdrant confirmation" — паттерн уже покрыт примером 2 (confirmation "Беру")
  - Пример 8 (строки 341-357): "ELK logs, past work skip" — паттерн покрыт `<definitions>` ("Completed work is NOT a new task")
* `LLM_WORKER_CONCURRENCY = 4` — ThreadPoolExecutor уже используется в main.py для батчей

## Requirements

* `process_batch`: если оба флага (`has_task` + `has_status_change`) — запускать `_extract_tasks` и `_extract_statuses` параллельно через `ThreadPoolExecutor(max_workers=2)`
* Если только один флаг — без изменений (параллелизация не нужна)
* Убрать пример 3 и пример 8 из `TASK_SYSTEM` (см. строки 253-269 и 341-357)
* Остальные 7 примеров не трогать — каждый покрывает уникальный паттерн

## Acceptance Criteria

* [ ] Батч с `has_task=True + has_status_change=True` обрабатывается параллельно (оба вызова стартуют одновременно)
* [ ] Результаты те же — порядок task events + status events не важен
* [ ] `TASK_SYSTEM` потерял ~50 строк (примеры 3 и 8)
* [ ] Синтаксис файлов OK (`python3 -m py_compile`)

## Technical Notes

* `llm-worker/processor.py` — `process_batch()`
* `llm-worker/llm/prompts.py` — `TASK_SYSTEM` examples
* Использовать `concurrent.futures.ThreadPoolExecutor` — уже в stdlib, не нужна новая зависимость
