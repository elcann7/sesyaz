export interface AudioDevice {
  index: number
  name: string
  isDefault: boolean
  sampleRate: number
}

export interface HistoryItem {
  id: string
  text: string
  model: string
  mode: string
  latencyMs: number
  durationSec: number
  targetApp: string
  createdAt: number
}

export interface AppConfigState {
  ptt_key: string
  toggle_hotkey: string
  dictation_mode: 'accurate' | 'polish'
  transcription_mode?: 'verbatim' | 'smart'
  language_mode: 'az-tech' | 'az' | 'en' | 'auto'
  typing_mode: 'smart' | 'unicode' | 'paste'
  auto_enter: boolean
  device_index: number | null
  autostart: boolean
  sound_cue: boolean
  pill_position: 'bottom' | 'top'
  custom_vocabulary: string[]
  apiKeyCount: number
  apiKeyPreviews: string[]
}

export type EngineStatus = 'idle' | 'recording' | 'transcribing' | 'done' | 'error'

export interface AppSnapshot {
  status: EngineStatus
  interimText?: string
  lastText: string
  lastError: string
  lastTargetApp: string
  lastLatencyMs: number
  totalTranscriptions: number
  totalWords: number
  minutesSaved: number
  config: AppConfigState
  devices: AudioDevice[]
  history: HistoryItem[]
}
