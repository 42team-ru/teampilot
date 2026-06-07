import type { ExtMessage } from '../types/messages'

export function sendToBackground(msg: ExtMessage): Promise<unknown> {
  return chrome.runtime.sendMessage(msg)
}

export function onMessage(
  handler: (msg: ExtMessage, sender: chrome.runtime.MessageSender) => unknown | Promise<unknown>
) {
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    const result = handler(msg as ExtMessage, sender)
    if (result instanceof Promise) {
      result.then(sendResponse).catch(() => sendResponse(null))
      return true
    }
  })
}
