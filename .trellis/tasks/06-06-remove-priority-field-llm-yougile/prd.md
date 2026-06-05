# remove priority field

## Goal

YouGile API не имеет поля priority — убрать его из LLM-воркера везде.

## Requirements

- `models.py`: убрать `priority` из `TaskCreateEvent` и `TaskExtraction`
- `llm/prompts.py`: убрать `<priority>` блок из системного промпта, поле из `output_format`, из всех примеров
- `tests/runner.py`: убрать проверку `priority`
- `tests/cases/*.json`: убрать `priority` из `expected_output` во всех 9 файлах

## Out of Scope

- Spring/Java не затронут (там `priority` нет)
- Замена на `color` в YouGile — не в этой задаче

## Technical Notes

- Файлы: `models.py`, `llm/prompts.py`, `tests/runner.py`, `tests/cases/*.json`
- Spring вообще не знает о priority — поле никогда не доходило до YouGile
