# Improve classifier prompt for mixed batches

## Goal

Classifier (cheap LLM) пропускает `has_status_change=True` когда батч содержит и новую задачу, и завершение старой. Также не распознаёт нестандартные completion-глаголы ("испек", "настроил", "разработал"). Нужно добавить реалистичных примеров в `CLASSIFIER_SYSTEM`.

## What I already know

* Файл: `llm-worker/llm/prompts.py`, константа `CLASSIFIER_SYSTEM`, блок `<examples>`
* Уже есть 13 примеров, включая один смешанный — но он синтетический: `"Есть и то и то"` — LLM не извлекает паттерн
* Сигналы `<has_status_change_true>` перечисляют только IT-глаголы: "сделал", "закрыл", "задеплоено" — нет "испек", "настроил", "разработал", "написал"
* `<calibration>` раздел описывает уровни уверенности корректно

## Requirements

* Добавить 3–4 реалистичных примера смешанных батчей (has_task=true + has_status_change=true одновременно)
* Добавить 2 примера нестандартных completion-глаголов (не IT-домен или нестандартное слово)
* Расширить сигналы `<has_status_change_true>` общими глаголами завершения
* Не менять логику — только промпт

## Acceptance Criteria

* [ ] Батч `["испек булки", "фронтенд переоткрыли нужно доделать", "я возьму"]` → has_task=true AND has_status_change=true
* [ ] Батч `["настроил деплой всё работает"]` → has_status_change=true
* [ ] Чистый task-батч без статуса → has_status_change=false (нет регрессии)

## Out of Scope

* Изменение порогов CLASSIFIER_THRESHOLD
* Изменение task/status chain промптов
