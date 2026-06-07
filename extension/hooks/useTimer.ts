import { useState, useEffect } from 'react'

export function useTimer(
  startedAt: number | undefined,
  totalPausedMs: number,
  pausedAt: number | undefined,
  active: boolean
): number {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!active || !startedAt) {
      setElapsed(0)
      return
    }
    const tick = () => {
      const pauseOffset = pausedAt ? Date.now() - pausedAt : 0
      setElapsed(Math.floor((Date.now() - startedAt - totalPausedMs - pauseOffset) / 1000))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [active, startedAt, totalPausedMs, pausedAt])

  return elapsed
}
