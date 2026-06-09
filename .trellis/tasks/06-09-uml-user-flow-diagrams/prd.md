# UML User Flow Diagrams

## Goal

Создать читаемые UML-схемы для всех ключевых пользовательских сценариев TeamPilot, чтобы наглядно показать взаимодействие акторов с системой.

## What I already know

- В README.md уже есть Mermaid sequence-диаграммы: главный сценарий чата→задачи, Chrome Extension meeting flow, Evening Sync flow
- Акторы: Manager (менеджер), Member (участник команды), Admin (владелец команды), Chrome Extension user
- Ключевые потоки:
  1. Онбординг — /start, создание/вступление в команду, привязка YouGile, инвайт-ссылки
  2. Чат → задачи — батчинг сообщений, LLM-классификация, auto-confirm ≥0.90, подтверждение кнопками ✅/✏️/❌
  3. Chrome Extension — pairing-code auth, запись встречи (tab+mic), real-time транскрипция, задачи в сайдпанели
  4. Вечерний синк — 18:00 промпт, отчёт участника, LLM-матчинг задач, черновик → подтверждение
  5. Аудио-встреча — загрузка MP3/OGG через бота, Whisper → задачи
  6. Управление задачами — /tasks, фильтр по колонке канбан, смена статуса
  7. Уведомления — дедлайн (2ч), стейл (24ч), вечерний дайджест
  8. Геймификация — XP за задачи, уровни, ачивки, /profile
  9. Рекомендации курсов — просроченная задача → Qdrant-поиск → курсы в ЛС
  10. База знаний — /wiki → FastAPI → Qdrant search → ответ

## Open Questions

_(resolved)_

## Decision (ADR-lite)

**Context**: Нужны UML-схемы для всех пользовательских сценариев TeamPilot
**Decision**: Activity diagrams в Mermaid (`flowchart TD`), файл `docs/user-flows.md`
**Consequences**: Рендерятся нативно на GitHub, README остаётся компактным, всё в одном месте

## Requirements

- Activity diagrams (Mermaid `flowchart TD`) для каждого из 10 сценариев
- Файл `docs/user-flows.md`
- Не дублировать sequence-диаграммы из README.md — activity-схемы дополняют их
- Акторы выделены отдельными нодами, системные компоненты — прямоугольниками
- Каждый сценарий — отдельный блок с заголовком H2

## Acceptance Criteria (evolving)

- [ ] Каждый из 10 юзерфлоу визуализирован отдельной схемой
- [ ] Схемы рендерятся без ошибок
- [ ] Акторы и системные компоненты чётко разделены

## Out of Scope

- Диаграммы классов (архитектурные)
- C4 диаграммы инфраструктуры

## Technical Notes

- README.md уже содержит 3 Mermaid sequence диаграммы (не дублировать)
- Mermaid поддерживается GitHub и большинством markdown-рендереров
- PlantUML мощнее для activity/state, но требует внешнего рендерера
