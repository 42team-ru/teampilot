export interface MicSettings {
  deviceId: string
  label: string
}

const KEY = 'micSettings'

export async function getMicSettings(): Promise<MicSettings | null> {
  const result = await chrome.storage.local.get(KEY)
  return (result[KEY] as MicSettings) ?? null
}

export async function setMicSettings(settings: MicSettings): Promise<void> {
  await chrome.storage.local.set({ [KEY]: settings })
}

export async function listMicrophones(): Promise<MediaDeviceInfo[]> {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    // permission may already be granted — ignore error
  }
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter((d) => d.kind === 'audioinput')
}
