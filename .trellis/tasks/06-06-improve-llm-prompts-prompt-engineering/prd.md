# Улучшение LLM-промптов по лучшим практикам prompt engineering

## Goal

Переработать три промпта в `llm-worker/llm/prompts.py` (CLASSIFIER, TASK, STATUS) на основе
официальных гайдов Anthropic и OpenAI по prompt engineering, чтобы повысить точность извлечения
задач и статусов из Telegram-чатов.

## What I already know

- Все три промпта живут в `llm-worker/llm/prompts.py`
- `safe_parser.py` уже стрипает `<thinking>` теги → безопасно добавить CoT в любой промпт
- TASK_SYSTEM уже использует `<thinking>` в примерах — хорошая база
- CLASSIFIER работает на cheap-модели (temperature=0.0, timeout=60s)
- TASK и STATUS — на expensive-модели (timeout=120s)
- Все промпты используют XML-теги — соответствует рекомендациям Anthropic
- Промпты богаты примерами (few-shot) — хорошо

## Конкретные улучшения (из анализа кода + best practices)

### CLASSIFIER_SYSTEM
1. Добавить `<thinking>` шаг перед JSON — Anthropic рекомендует CoT даже для классификаторов;
   safe_parser стрипает тег → backward compatible
2. Уточнить output format: заменить `bool` на `true|false` (более явно для модели)
3. Добавить `<calibration>` гайдлайн для confidence scores (сейчас нет руководства о том,
   когда ставить 0.5 vs 0.9)
4. Добавить 1–2 трудных примера (вопрос без явного назначения, прошедшее время)

### TASK_SYSTEM
1. `<source_message_ids>` секция написана по-русски — остальной промпт на английском,
   нужна единообразность → перевести на английский
2. Уточнить что `<thinking>` — ОБЯЗАТЕЛЕН, а не опционален
3. В `<language_and_format>`: явно указать "thinking — любой язык, output — русский"
4. В output_format: заменить `12345` → `integer` для типа assignee_id

### STATUS_SYSTEM
1. Добавить `<thinking>` во все примеры (сейчас примеры без CoT — в отличие от TASK)
2. Добавить 1–2 примера для edge cases:
   - ASSIGN когда есть role ambiguity
   - Несколько статус-изменений в одном батче разных задач
3. Добавить явную инструкцию про `<thinking>` в `<task>` секцию

## Decision (ADR-lite)

**Context**: CLASSIFIER — это быстрый фильтр первого уровня на cheap-модели, работает на каждом батче.
**Decision**: НЕ добавлять `<thinking>` в CLASSIFIER. False positive → expensive-модель вернёт []. 
Thinking нужен только там где сложная логика (assignee resolution, column selection) — это TASK/STATUS.
**Consequences**: CLASSIFIER остаётся быстрым; точность улучшается через лучшие примеры, не CoT.

## Requirements

- [ ] CLASSIFIER: добавить 1–2 трудных примера (прошедшее время, вопрос без назначения)
- [ ] CLASSIFIER: fix output_format (bool → true|false)
- [ ] CLASSIFIER: добавить calibration guidance
- [ ] TASK: fix source_message_ids на английский
- [ ] TASK: уточнить обязательность <thinking> и язык вывода
- [ ] STATUS: добавить <thinking> в примеры
- [ ] STATUS: 1-2 новых edge case примера

## Acceptance Criteria

- [ ] Промпты проходят существующие тесты в `llm-worker/tests/`
- [ ] Все `{placeholder}` переменные остаются нетронутыми
- [ ] Python `{{` / `}}` escaping для literal braces сохранён
- [ ] Каждый промпт всё ещё парсится safe_parser без ошибок

## Definition of Done

- Все три промпта обновлены
- Существующие тесты зелёные
- Изменения не меняют поведение processor.py (только промпт текст)

## Out of Scope

- Добавление новых промптов (транскрипт и т.д.)
- Изменения в chains.py, processor.py
- Тюнинг threshold-параметров в settings.py

## Technical Notes

- Файл: `llm-worker/llm/prompts.py`
- Parser: `llm-worker/llm/safe_parser.py` — стрипает `<thinking>` через regex
- Best practices sources: Anthropic docs, OpenAI prompt engineering guide
- Тесты: `llm-worker/tests/`
