import { useEffect } from 'react'

const IDLE_MS = 5 * 60 * 1000
const ACTIVITY_EVENTS = ['pointerdown', 'pointermove', 'keydown', 'input', 'wheel', 'touchstart']

// Solo se monta en el login. El reloj también cuenta el tiempo en otra pestaña.
export function useLoginIdle(onIdle, paused) {
  useEffect(() => {
    if (paused) return
    let deadline = Date.now() + IDLE_MS
    let timer
    function schedule() {
      clearTimeout(timer)
      timer = setTimeout(check, Math.max(0, deadline - Date.now()))
    }
    function check() {
      if (Date.now() >= deadline) { onIdle(); return }
      schedule()
    }
    function activity() {
      if (Date.now() >= deadline) { onIdle(); return }
      deadline = Date.now() + IDLE_MS
      schedule()
    }
    function visible() {
      if (document.visibilityState === 'visible') check()
    }
    schedule()
    for (const event of ACTIVITY_EVENTS) window.addEventListener(event, activity, { passive: true })
    window.addEventListener('focus', check)
    document.addEventListener('visibilitychange', visible)
    return () => {
      clearTimeout(timer)
      for (const event of ACTIVITY_EVENTS) window.removeEventListener(event, activity)
      window.removeEventListener('focus', check)
      document.removeEventListener('visibilitychange', visible)
    }
  }, [onIdle, paused])
}
