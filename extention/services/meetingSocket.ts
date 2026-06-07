import { Client, type IMessage, type StompSubscription } from '@stomp/stompjs'
import { getWebSocketUrl } from './config'
import type { MeetingAudioChunkPayload, MeetingLiveResult } from '../types/recording'

interface ConnectOptions {
  meetingId: string
  token: string
  onResult: (event: MeetingLiveResult) => void | Promise<void>
  onDisconnect?: () => void | Promise<void>
  onError?: (error: Error) => void | Promise<void>
}

let client: Client | null = null
let subscription: StompSubscription | null = null
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
        subscription = client.subscribe(
          `/topic/meetings/${options.meetingId}/results`,
          (message) => handleMessage(message, options)
        )
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
  subscription?.unsubscribe()
  subscription = null
  activeMeetingId = null

  if (!client) return
  const current = client
  client = null
  if (current.active) {
    await current.deactivate()
  }
}

function handleMessage(message: IMessage, options: ConnectOptions) {
  try {
    const event = JSON.parse(message.body) as MeetingLiveResult
    options.onResult(event)
  } catch (e) {
    const error = e instanceof Error ? e : new Error(String(e))
    options.onError?.(error)
  }
}
