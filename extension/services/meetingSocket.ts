import { Client, type IMessage, type StompSubscription } from '@stomp/stompjs'
import { getWebSocketUrl } from './config'
import type { MeetingAudioChunkPayload, MeetingLiveResult, TaskStatusUpdate } from '../types/recording'

interface ConnectOptions {
  meetingId: string
  teamId: string
  token: string
  onResult: (event: MeetingLiveResult) => void | Promise<void>
  onTaskUpdate?: (event: TaskStatusUpdate) => void | Promise<void>
  onDisconnect?: () => void | Promise<void>
  onError?: (error: Error) => void | Promise<void>
}

let client: Client | null = null
let meetingSubscription: StompSubscription | null = null
let teamSubscription: StompSubscription | null = null
let activeMeetingId: string | null = null

export async function connectMeetingSocket(options: ConnectOptions): Promise<void> {
  if (client?.connected && activeMeetingId === options.meetingId) return

  await disconnectMeetingSocket()

  activeMeetingId = options.meetingId

  await new Promise<void>((resolve, reject) => {
    let settled = false
    client = new Client({
      brokerURL: getWebSocketUrl(),
      connectHeaders: {
        Authorization: `Bearer ${options.token}`,
      },
      reconnectDelay: 3000,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,
      debug: () => {},
      onConnect: () => {
        if (!client) return
        meetingSubscription = client.subscribe(
          `/topic/meetings/${options.meetingId}/results`,
          (message) => handleMeetingMessage(message, options)
        )
        if (options.onTaskUpdate) {
          teamSubscription = client.subscribe(
            `/topic/teams/${options.teamId}/task-updates`,
            (message) => handleTaskUpdateMessage(message, options)
          )
        }
        settled = true
        resolve()
      },
      onStompError: (frame) => {
        const message = frame.headers.message || frame.body || 'STOMP connection failed'
        const error = new Error(message)
        options.onError?.(error)
        if (!settled) {
          settled = true
          reject(error)
        }
      },
      onWebSocketClose: () => {
        options.onDisconnect?.()
      },
      onWebSocketError: () => {
        const error = new Error('WebSocket connection failed')
        options.onError?.(error)
        if (!settled) {
          settled = true
          reject(error)
        }
      },
    })

    client.activate()
  })
}

export function sendMeetingChunk(meetingId: string, payload: MeetingAudioChunkPayload): void {
  if (!client?.connected) {
    throw new Error('WebSocket ещё не подключён')
  }
  client.publish({
    destination: `/app/meetings/${meetingId}/chunks`,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function disconnectMeetingSocket(): Promise<void> {
  meetingSubscription?.unsubscribe()
  meetingSubscription = null
  teamSubscription?.unsubscribe()
  teamSubscription = null
  activeMeetingId = null

  if (!client) return
  const current = client
  client = null
  if (current.active) {
    await current.deactivate()
  }
}

function handleMeetingMessage(message: IMessage, options: ConnectOptions) {
  try {
    const event = JSON.parse(message.body) as MeetingLiveResult
    options.onResult(event)
  } catch (e) {
    const error = e instanceof Error ? e : new Error(String(e))
    options.onError?.(error)
  }
}

function handleTaskUpdateMessage(message: IMessage, options: ConnectOptions) {
  try {
    const event = JSON.parse(message.body) as TaskStatusUpdate
    options.onTaskUpdate?.(event)
  } catch (e) {
    const error = e instanceof Error ? e : new Error(String(e))
    options.onError?.(error)
  }
}
