import type { MeetingResults } from '../types/recording'

let _meetingCounter = 0

export async function startMeeting(_title: string): Promise<{ meetingId: string }> {
  _meetingCounter++
  return { meetingId: `mock-meeting-${_meetingCounter}-${Date.now()}` }
}

export async function sendChunk(_meetingId: string, _blob: Blob, _chunkIndex: number): Promise<void> {
  // no-op until backend is ready
}

export async function finishMeeting(_meetingId: string): Promise<void> {
  // no-op until backend is ready
}

export async function getMeetingResults(meetingId: string): Promise<MeetingResults> {
  return {
    meetingId,
    duration: 45 * 60 * 1000,
    tasks: [
      {
        id: '1',
        title: 'Реализовать интеграцию с YouGile API',
        assignee: 'Иван Петров',
        deadline: '2026-06-10',
        confidence: 0.92,
        source: '17:04 — Обсуждение интеграций',
        status: 'pending',
      },
      {
        id: '2',
        title: 'Настроить Kafka-топики для обработки сообщений',
        assignee: undefined,
        deadline: '2026-06-08',
        confidence: 0.78,
        source: '17:12 — Архитектурное обсуждение',
        status: 'incomplete',
      },
      {
        id: '3',
        title: 'Написать документацию по API расширения',
        assignee: 'Мария Сидорова',
        deadline: undefined,
        confidence: 0.65,
        source: '17:28 — Финальное обсуждение',
        status: 'pending',
      },
    ],
    decisions: [
      { id: 'd1', text: 'Используем Spring Boot для бэкенда', timestamp: '17:06' },
      { id: 'd2', text: 'Используем Telegram Bot для нотификаций', timestamp: '17:14' },
      { id: 'd3', text: 'Отказываемся от Playwright в пользу WXT', timestamp: '17:21' },
      { id: 'd4', text: 'Chrome Extension записывает только звук вкладки по умолчанию', timestamp: '17:30' },
    ],
    liveEvents: [
      { id: 'e1', time: '17:02', text: 'Обсуждается интеграция с Telegram', type: 'event' },
      { id: 'e2', time: '17:06', text: 'Принято решение использовать Spring Boot', type: 'event' },
      { id: 'e3', time: '17:09', text: 'Обсуждается Kanban интеграция', type: 'event' },
      { id: 'e4', time: '17:12', text: 'Не найден ответственный для задачи по Kafka', type: 'alert' },
      { id: 'e5', time: '17:15', text: 'Обсуждается архитектура расширения', type: 'event' },
      { id: 'e6', time: '17:21', text: 'Решение: использовать WXT вместо Playwright', type: 'event' },
      { id: 'e7', time: '17:28', text: 'Не указан дедлайн для задачи по документации', type: 'alert' },
      { id: 'e8', time: '17:30', text: 'Финальное обсуждение MVP функций', type: 'event' },
    ],
    summary: {
      goal: 'Определить архитектуру и MVP-функционал AI PM Assistant для хакатона',
      topics: [
        'Интеграция с Telegram Bot API',
        'Архитектура Spring Boot монолита',
        'YouGile Kanban интеграция',
        'Chrome Extension для записи встреч',
        'Kafka-топики для обмена сообщениями',
      ],
      decisions: [
        'Spring Boot для бэкенда',
        'Telegram Bot для нотификаций',
        'WXT для Chrome Extension',
        'Запись только звука вкладки по умолчанию',
      ],
      risks: [
        'Ограниченное время хакатона — возможен недострой части функций',
        'Нет ответственного по Kafka-интеграции',
      ],
      nextSteps: [
        'Реализовать /meetings/* эндпоинты на бэкенде',
        'Настроить Kafka-топики',
        'Подключить YouGile API',
        'Провести интеграционное тестирование',
      ],
    },
  }
}

export async function createTask(_meetingId: string, _taskId: string): Promise<void> {
  // no-op until backend is ready
}
