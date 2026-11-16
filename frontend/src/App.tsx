import React, { useEffect, useState } from 'react'
import { fetchState } from './api'
import { PillView } from './components/PillView'
import { StudioView } from './components/StudioView'
import { AppSnapshot } from './types'

const INITIAL_SNAPSHOT: AppSnapshot = {
  status: 'idle',
  interimText: '',
  lastText: '',
  lastError: '',
  lastTargetApp: '',
  lastLatencyMs: 0,
  totalTranscriptions: 0,
  totalWords: 0,
  minutesSaved: 0,
  config: {
    ptt_key: 'rctrl',
    toggle_hotkey: 'ctrl+shift+space',
    dictation_mode: 'accurate',
    language_mode: 'az-tech',
    typing_mode: 'smart',
    auto_enter: false,
    device_index: null,
    autostart: true,
    sound_cue: true,
    pill_position: 'bottom',
    custom_vocabulary: [],
    apiKeyCount: 0,
    apiKeyPreviews: [],
  },
  devices: [],
  history: [],
}

export function App() {
  const isPill = new URLSearchParams(window.location.search).get('view') === 'pill'
  const [snapshot, setSnapshot] = useState<AppSnapshot>(INITIAL_SNAPSHOT)
  const [rms, setRms] = useState(0)
  const [bands, setBands] = useState<number[]>(Array(16).fill(0))
  const [capturingField, setCapturingField] = useState<string | null>(null)

  useEffect(() => {
    let es: EventSource | null = null
    let closed = false

    fetchState()
      .then((s) => {
        if (!closed) setSnapshot(s)
      })
      .catch(() => {})

    const connect = () => {
      if (closed) return
      es = new EventSource('/events')
      es.addEventListener('snapshot', (e) => {
        try {
          setSnapshot(JSON.parse((e as MessageEvent).data))
        } catch {}
      })
      es.addEventListener('history', (e) => {
        try {
          setSnapshot(JSON.parse((e as MessageEvent).data))
        } catch {}
      })
      es.addEventListener('status', (e) => {
        try {
          const patch = JSON.parse((e as MessageEvent).data)
          setSnapshot((prev) => ({ ...prev, ...patch }))
        } catch {}
      })
      es.addEventListener('level', (e) => {
        try {
          const lvl = JSON.parse((e as MessageEvent).data)
          setRms(lvl.rms || 0)
          if (Array.isArray(lvl.bands)) setBands(lvl.bands)
        } catch {}
      })
      es.addEventListener('hotkey_captured', () => {
        setCapturingField(null)
      })
      es.onerror = () => {
        es?.close()
        if (!closed) setTimeout(connect, 1000)
      }
    }

    connect()
    return () => {
      closed = true
      es?.close()
    }
  }, [])

  if (isPill) {
    return <PillView snapshot={snapshot} rms={rms} bands={bands} />
  }

  return (
    <StudioView
      snapshot={snapshot}
      setSnapshot={setSnapshot}
      rms={rms}
      bands={bands}
      capturingField={capturingField}
      setCapturingField={setCapturingField}
    />
  )
}

export default App
