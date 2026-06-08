# Extension Realtime Events UX

## Goal

Менеджер в side panel расширения видит в реальном времени события текущей встречи: новые задачи от LLM, одобрения/отклонения задач менеджером через Telegram, контекст встречи. Всё работает только во время активного звонка.

## Requirements

1. **Backend — новый STOMP топик для задач команды:**
   - `EveningSyncService.approveTask()` → STOMP broadcast на `/topic/teams/{teamId}/task-updates` с payload `{taskId, title, status: "APPROVED", approvedBy}`
   - `EveningSyncService.rejectTask()` → STOMP broadcast на `/topic/teams/{teamId}/task-updates` с payload `{taskId, title, status: "REJECTED"}`
   - `TaskService.createFromLlmEvent()` → STOMP broadcast на `/topic/teams/{teamId}/task-updates` с payload `{taskId, title, status: "CREATED"}`

2. **Extension — вторая STOMP-подписка во время звонка:**
   - `meetingSocket.ts`: добавить подписку `/topic/teams/{teamId}/task-updates` при коннекте
   - Новый callback `onTaskUpdate: (event: TaskStatusUpdate) => void`
   - Отписка при `disconnectMeetingSocket()`

3. **Extension UX — Toast:**
   - Toast-компонент в side panel появляется на 3-5 сек при новом событии
   - Разные стили: success (одобрено), destructive (отклонено), info (новая задача)
   - Стек до 3 тостов одновременно

4. **Extension UX — Notification badge:**
   - `chrome.action.setBadgeText({text: "N"})` при новом событии когда panel закрыт
   - Красный background badge
   - Сброс при открытии side panel

5. **Extension UX — Context field:**
   - Поле `context` из `MeetingLiveResult` добавить в LiveTab (сейчас игнорируется)
   - Отображать как событие типа `'context'` — серый стиль, отличный от transcript и alert

6. **Extension UX — Читаемые статус-алерты:**
   - Вместо "Обновление статуса задачи: ACTION" → человекочитаемый текст
   - "Задача одобрена менеджером", "Задача создана: X", "Задача отклонена"

## Acceptance Criteria

- [ ] При одобрении задачи в Telegram → в extension появляется toast "Задача одобрена" и badge на иконке
- [ ] При создании задачи LLM → в extension появляется toast "Новая задача: {title}"
- [ ] Поле `context` из `MeetingLiveResult` отображается в LiveTab
- [ ] Badge сбрасывается при открытии side panel
- [ ] Всё работает только во время активного звонка, вне звонка — ничего

## Out of Scope

- Desktop notifications (chrome.notifications API)
- Курсы и рекомендации
- Async-события вне звонка (persistent background connection)
- Изменение схемы БД

## Technical Approach

**Backend:**
- Внедрить `SimpMessagingTemplate` в `EveningSyncService` и `TaskService`
- Новый DTO: `TaskUpdateMessage {taskId, title, status, actorName?}`
- Broadcast на `/topic/teams/{teamId}/task-updates`

**Extension:**
- `meetingSocket.ts`: `ConnectOptions` получает `teamId` и `onTaskUpdate` callback; добавляется вторая подписка
- Новый тип `TaskStatusUpdate {taskId: string, title: string, status: 'CREATED'|'APPROVED'|'REJECTED', actorName?: string}`
- Новый hook `useToasts()` или простой state в sidepanel App.tsx
- Toast рендерится поверх контента side panel (fixed/absolute позиционирование)
- Badge: `chrome.action.setBadgeText` вызывается из background.ts

## Technical Notes

**Ключевые файлы:**
- `extension/services/meetingSocket.ts` — добавить teamId + вторую подписку
- `extension/entrypoints/sidepanel/App.tsx` — добавить toast state
- `extension/entrypoints/background.ts` — обработка badge
- `extension/services/storage.ts` — `applyMeetingLiveResult` (добавить context)
- `extension/components/sidepanel/LiveTab.tsx` — добавить type='context'
- `backend/.../service/EveningSyncService.java` — добавить STOMP broadcast
- `backend/.../service/TaskService.java` — добавить STOMP broadcast
- `backend/.../websocket/MeetingWebSocketController.java` — пример STOMP broadcast паттерна
- `backend/.../kafka/consumer/MeetingLiveResultConsumer.java` — пример Kafka→STOMP
