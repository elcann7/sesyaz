import React, { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AudioLines,
  BookOpen,
  Check,
  Copy,
  History,
  Keyboard,
  KeyRound,
  Mic,
  Minus,
  Plus,
  Settings,
  Trash2,
  Wand2,
  X,
} from 'lucide-react'
import { postAction } from '../api'
import { AppSnapshot, AppConfigState } from '../types'
import { AudioOrb } from './AudioOrb'
import { AuroraCanvas } from './reactbits/AuroraCanvas'
import { BlurText } from './reactbits/BlurText'
import { CountUp } from './reactbits/CountUp'
import { DecryptedText } from './reactbits/DecryptedText'
import { DockItemData, MacDock } from './reactbits/MacDock'
import { Magnet } from './reactbits/Magnet'
import { ParticlesField } from './reactbits/ParticlesField'
import { SpotlightCard } from './reactbits/SpotlightCard'

interface StudioViewProps {
  snapshot: AppSnapshot
  setSnapshot: React.Dispatch<React.SetStateAction<AppSnapshot>>
  rms: number
  bands: number[]
  capturingField: string | null
  setCapturingField: (f: string | null) => void
}

type TabId = 'studio' | 'history' | 'vocabulary' | 'settings'

const formatHotkeyLabel = (raw: string): string =>
  raw
    .split('+')
    .map((p) => {
      const m: Record<string, string> = {
        rctrl: 'Right Ctrl',
        lctrl: 'Left Ctrl',
        ralt: 'Right Alt',
        lalt: 'Left Alt',
        rshift: 'Right Shift',
        lshift: 'Left Shift',
        ctrl: 'Ctrl',
        shift: 'Shift',
        alt: 'Alt',
        space: 'Space',
      }
      return m[p.toLowerCase()] || p.toUpperCase()
    })
    .join(' + ')

export const StudioView: React.FC<StudioViewProps> = ({
  snapshot,
  setSnapshot,
  rms,
  bands,
  capturingField,
  setCapturingField,
}) => {
  const [tab, setTab] = useState<TabId>('studio')
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [vocabDraft, setVocabDraft] = useState('')
  const [apiKeyDraft, setApiKeyDraft] = useState('')
  const [testDraft, setTestDraft] = useState('')

  const { config, status, lastText, lastError, history, devices } = snapshot
  const isRec = status === 'recording'

  const updateConfig = async (patch: Partial<AppConfigState> & Record<string, unknown>) => {
    const next = await postAction<AppSnapshot>('/api/config', patch)
    setSnapshot(next)
  }

  const startCapture = async (field: 'ptt_key' | 'toggle_hotkey') => {
    setCapturingField(field)
    await postAction('/api/hotkey/capture', { field })
  }

  const copyText = async (text: string, id: string) => {
    let ok = false
    try {
      await postAction('/api/clipboard/copy', { text })
      ok = true
    } catch {
      // fallback to browser clipboard
    }
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
        ok = true
      }
    } catch {
      // ignore if restricted inside webview
    }
    if (ok) {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 1200)
    }
  }

  const dockItems: DockItemData[] = useMemo(
    () => [
      { id: 'studio', label: 'Studio', icon: <AudioLines className="h-5 w-5" /> },
      { id: 'history', label: 'History', icon: <History className="h-5 w-5" />, badge: history.length },
      { id: 'vocabulary', label: 'Vocabulary', icon: <BookOpen className="h-5 w-5" /> },
      { id: 'settings', label: 'Settings', icon: <Settings className="h-5 w-5" /> },
    ],
    [history.length]
  )

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-[20px] border border-white/[0.11] bg-[#0a0a0b] text-[#f4f4f6] shadow-[0_24px_80px_rgba(0,0,0,0.85)]">
      <AuroraCanvas active={isRec || status === 'transcribing'} rms={rms} />
      <ParticlesField rms={rms} recording={isRec} />

      {/* Custom Frameless Drag Titlebar */}
      <header
        onMouseDown={(e) => {
          if ((e.target as HTMLElement).closest('button')) return
          postAction('/api/window/drag')
        }}
        className="relative z-20 flex h-13 shrink-0 cursor-grab items-center justify-between border-b border-white/[0.07] bg-[#0d0d10]/85 px-5 backdrop-blur-xl active:cursor-grabbing"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/15 bg-white/[0.06] text-[#f4f4f6]">
            <AudioLines className="h-4 w-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-[15px] font-bold tracking-tight">SesYaz</span>
            <span className="font-mono-tech text-[10px] uppercase tracking-widest text-[#5c5c66]">
              WIN32 · LIVE STT
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px]">
            <span
              className={`h-2 w-2 rounded-full ${
                isRec
                  ? 'animate-pulse bg-[#f4f4f6]'
                  : status === 'transcribing'
                    ? 'animate-ping bg-[#c4c4cc]'
                    : config.apiKeyCount > 0
                      ? 'bg-[#e4e4e8]'
                      : 'bg-[#5c5c66]'
              }`}
            />
            <span className="font-mono-tech text-[#9898a4]">
              {isRec
                ? 'LISTENING'
                : status === 'transcribing'
                  ? 'FINALIZING'
                  : config.dictation_mode === 'accurate'
                    ? 'gemini-3.5-transcribe-live'
                    : 'Live STT + Flash Lite'}
            </span>
          </div>

          <button
            type="button"
            title="Minimize"
            onClick={() => postAction('/api/window/minimize')}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-[#9898a4] transition hover:border-white/25 hover:text-white"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            title="Hide to System Tray"
            onClick={() => postAction('/api/window/hide')}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-[#9898a4] transition hover:border-white/30 hover:text-white"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {/* Main Content Stage */}
      <main className="studio-scroll relative z-10 flex-1 overflow-y-auto px-7 pb-24 pt-5">
        <AnimatePresence mode="wait">
          {tab === 'studio' ? (
            <motion.div
              key="studio"
              initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
              transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto flex max-w-4xl flex-col gap-5"
            >
              {/* Hero Audio-Reactive Stage */}
              <SpotlightCard className="p-6">
                <div className="flex flex-col items-center gap-6 md:flex-row md:justify-between">
                  <div className="flex-1 space-y-3">
                    <h1 className="font-display text-[26px] font-bold leading-tight tracking-tight">
                      <span className="text-[#9898a4]">
                        <BlurText text="System-Wide Voice," delay={0.04} />
                      </span>
                      <br />
                      <span className="text-[#f4f4f6]">
                        <BlurText text="Live text injection." delay={0.05} />
                      </span>
                    </h1>
                    <p className="max-w-lg text-[13px] leading-relaxed text-[#9898a4]">
                      Hold{' '}
                      <span className="rounded border border-white/15 bg-white/[0.06] px-1.5 py-0.5 font-mono-tech text-[11.5px] text-[#f4f4f6]">
                        {formatHotkeyLabel(config.ptt_key)}
                      </span>{' '}
                      and speak — text streams straight to your focused window cursor.
                    </p>

                    {/* Mode Selector Pills */}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Magnet strength={0.16} padding={18}>
                        <button
                          type="button"
                          onClick={() => updateConfig({ dictation_mode: 'accurate' })}
                          className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3.5 py-2 text-[12px] font-semibold transition ${
                            config.dictation_mode === 'accurate'
                              ? 'border-[#f4f4f6] bg-[#f4f4f6] text-[#0a0a0b]'
                              : 'border-white/10 bg-white/[0.03] text-[#9898a4] hover:border-white/25 hover:text-white'
                          }`}
                        >
                          <Mic className="h-3.5 w-3.5" />
                          Direct Live STT
                        </button>
                      </Magnet>
                      <Magnet strength={0.16} padding={18}>
                        <button
                          type="button"
                          onClick={() => updateConfig({ dictation_mode: 'polish' })}
                          className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3.5 py-2 text-[12px] font-semibold transition ${
                            config.dictation_mode === 'polish'
                              ? 'border-[#f4f4f6] bg-[#f4f4f6] text-[#0a0a0b]'
                              : 'border-white/10 bg-white/[0.03] text-[#9898a4] hover:border-white/25 hover:text-white'
                          }`}
                        >
                          <Wand2 className="h-3.5 w-3.5" />
                          Polished (Flash Lite)
                        </button>
                      </Magnet>
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-5 pr-2">
                    <AudioOrb
                      status={status}
                      rms={rms}
                      bands={bands}
                      onToggle={() => postAction('/api/record/toggle', { fromStudio: true })}
                    />
                    <span className="font-mono-tech text-[11px] text-[#9898a4]">
                      {isRec
                        ? 'Click to finish'
                        : status === 'transcribing'
                          ? 'Processing...'
                          : 'Mic test'}
                    </span>
                  </div>
                </div>
              </SpotlightCard>

              {/* Two Interactive Trigger & Live Sandbox Cards */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <SpotlightCard className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-mono-tech text-[10px] uppercase tracking-wider text-[#5c5c66]">
                        HOTKEYS
                      </span>
                      <h3 className="font-display mt-1 text-[16px] font-semibold">
                        Global controls
                      </h3>
                    </div>
                    <Keyboard className="h-4 w-4 text-[#9898a4]" />
                  </div>

                  <div className="mt-4 space-y-2.5 text-[12.5px]">
                    <div className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-3.5 py-2.5">
                      <span className="text-[#9898a4]">Push-to-Talk</span>
                      <span className="rounded-lg border border-white/25 bg-white/[0.08] px-2.5 py-0.5 font-mono-tech text-[11px] font-semibold text-[#f4f4f6]">
                        {formatHotkeyLabel(config.ptt_key)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-3.5 py-2.5">
                      <span className="text-[#9898a4]">Toggle Record</span>
                      <span className="rounded-lg border border-white/15 bg-white/[0.04] px-2.5 py-0.5 font-mono-tech text-[11px] font-semibold text-[#c4c4cc]">
                        {formatHotkeyLabel(config.toggle_hotkey)}
                      </span>
                    </div>
                  </div>
                </SpotlightCard>

                <SpotlightCard className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-mono-tech text-[10px] uppercase tracking-wider text-[#5c5c66]">
                        SESSION
                      </span>
                      <h3 className="font-display mt-1 text-[16px] font-semibold">
                        <CountUp to={snapshot.totalWords} /> words ·{' '}
                        <span className="text-[#c4c4cc]">
                          <CountUp to={snapshot.totalTranscriptions} /> clips
                        </span>
                      </h3>
                    </div>
                    {snapshot.lastLatencyMs ? (
                      <span className="rounded-md border border-white/10 bg-white/[0.05] px-2 py-0.5 font-mono-tech text-[10px] text-[#c4c4cc]">
                        {snapshot.lastLatencyMs} ms
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-3">
                    {lastError ? (
                      <p className="rounded-xl border border-white/15 bg-[#181213] p-2.5 text-[12px] text-[#e4e4e8]">
                        {lastError}
                      </p>
                    ) : lastText ? (
                      <div className="rounded-xl border border-white/10 bg-[#0d0d10] p-3">
                        <div className="mb-1 flex items-center justify-between">
                          <span className="font-mono-tech text-[10px] text-[#5c5c66]">
                            LAST RESULT
                          </span>
                          <button
                            type="button"
                            onClick={() => copyText(lastText, 'latest')}
                            className="flex cursor-pointer items-center gap-1 text-[11px] text-[#9898a4] hover:text-white"
                          >
                            {copiedId === 'latest' ? (
                              <Check className="h-3 w-3 text-[#f4f4f6]" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                            Copy
                          </button>
                        </div>
                        <DecryptedText
                          text={lastText}
                          className="block text-[13px] leading-relaxed text-[#f4f4f6]"
                        />
                      </div>
                    ) : (
                      <input
                        value={testDraft}
                        onChange={(e) => setTestDraft(e.target.value)}
                        placeholder={`Scratchpad — test with ${formatHotkeyLabel(config.ptt_key)}`}
                        className="w-full rounded-xl border border-white/10 bg-[#0d0d10] px-3.5 py-3 text-[12.5px] text-[#f4f4f6] placeholder-[#5c5c66] outline-none transition focus:border-white/35"
                      />
                    )}
                  </div>
                </SpotlightCard>
              </div>
            </motion.div>
          ) : tab === 'history' ? (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
              transition={{ duration: 0.22 }}
              className="mx-auto flex max-w-4xl flex-col gap-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-xl font-bold">Dictation History</h2>
                  <p className="text-[12px] text-[#a1a5b3]">
                    Last {history.length} voice clips · Saved locally automatically
                  </p>
                </div>
                {history.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => postAction('/api/history/clear').then((s) => setSnapshot(s as AppSnapshot))}
                    className="flex cursor-pointer items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[12px] text-[#a1a5b3] transition hover:border-red-400/40 hover:text-red-300"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Clear all
                  </button>
                ) : null}
              </div>

              {history.length === 0 ? (
                <SpotlightCard className="p-10 text-center">
                  <p className="text-[14px] text-[#a1a5b3]">
                    No transcriptions yet. Hold your hotkey and speak a sentence!
                  </p>
                </SpotlightCard>
              ) : (
                <div className="space-y-2.5">
                  {history.map((item, idx) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: Math.min(idx * 0.03, 0.25) }}
                    >
                      <SpotlightCard className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <p className="text-[13.5px] leading-relaxed text-[#f4f2ed]">{item.text}</p>
                          <div className="flex shrink-0 items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => copyText(item.text, item.id)}
                              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-[#9898a4] hover:text-white"
                            >
                              {copiedId === item.id ? (
                                <Check className="h-3.5 w-3.5 text-[#f4f4f6]" />
                              ) : (
                                <Copy className="h-3.5 w-3.5" />
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                postAction<AppSnapshot>('/api/history/delete', { id: item.id }).then(setSnapshot)
                              }
                              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-[#9898a4] hover:border-white/30 hover:text-white"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                        <div className="mt-2.5 flex flex-wrap items-center gap-2.5 font-mono-tech text-[10px] text-[#5c5c66]">
                          <span className="text-[#c4c4cc]">{item.targetApp}</span>
                          <span>•</span>
                          <span>{item.model}</span>
                          <span>•</span>
                          <span>{item.latencyMs}ms</span>
                          <span>•</span>
                          <span>{new Date(item.createdAt).toLocaleTimeString('en-US')}</span>
                        </div>
                      </SpotlightCard>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          ) : tab === 'vocabulary' ? (
            <motion.div
              key="vocabulary"
              initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
              transition={{ duration: 0.22 }}
              className="mx-auto flex max-w-4xl flex-col gap-4"
            >
              <div>
                <h2 className="font-display text-xl font-bold">Custom Vocabulary</h2>
                <p className="text-[12.5px] text-[#a1a5b3]">
                  Terms listed here bias Gemini Live Speech-to-Text so libraries, project names,
                  and symbols are transcribed accurately.
                </p>
              </div>

              <SpotlightCard className="p-5">
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const word = vocabDraft.trim()
                    if (!word) return
                    if (!config.custom_vocabulary.includes(word)) {
                      updateConfig({ custom_vocabulary: [...config.custom_vocabulary, word] })
                    }
                    setVocabDraft('')
                  }}
                  className="flex gap-2.5"
                >
                  <input
                    value={vocabDraft}
                    onChange={(e) => setVocabDraft(e.target.value)}
                    placeholder="Add term (e.g. Supabase, Docker, FastAPI)..."
                    className="flex-1 rounded-xl border border-white/12 bg-[#0d0d10] px-4 py-2.5 text-[13px] text-[#f4f4f6] placeholder-[#5c5c66] outline-none focus:border-white/35"
                  />
                  <Magnet strength={0.18} padding={18}>
                    <button
                      type="submit"
                      className="flex cursor-pointer items-center gap-1.5 rounded-xl bg-[#f4f4f6] px-4 py-2.5 text-[13px] font-bold text-[#0a0a0b] transition hover:bg-white"
                    >
                      <Plus className="h-4 w-4" />
                      Add
                    </button>
                  </Magnet>
                </form>

                <div className="mt-5 flex flex-wrap gap-2">
                  <AnimatePresence>
                    {config.custom_vocabulary.map((term) => (
                      <motion.span
                        key={term}
                        layout
                        initial={{ opacity: 0, scale: 0.85 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.04] px-3 py-1.5 text-[12px] text-[#f4f2ed]"
                      >
                        <span>{term}</span>
                        <button
                          type="button"
                          onClick={() =>
                            updateConfig({
                              custom_vocabulary: config.custom_vocabulary.filter((w) => w !== term),
                            })
                          }
                          className="cursor-pointer text-[#656a78] hover:text-red-300"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </motion.span>
                    ))}
                  </AnimatePresence>
                </div>
              </SpotlightCard>
            </motion.div>
          ) : (
            <motion.div
              key="settings"
              initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
              transition={{ duration: 0.22 }}
              className="mx-auto grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-2"
            >
              {/* Hotkeys & Microphone */}
              <SpotlightCard className="space-y-4 p-5">
                <h3 className="font-display text-[15px] font-semibold">Hotkeys & Microphone</h3>

                <div className="space-y-2">
                  <label className="block text-[11.5px] text-[#a1a5b3]">
                    Push-to-Talk key (hold to speak, release to inject)
                  </label>
                  <button
                    type="button"
                    onClick={() => startCapture('ptt_key')}
                    className={`w-full cursor-pointer rounded-xl border px-3.5 py-2.5 text-left font-mono-tech text-[12px] transition ${
                      capturingField === 'ptt_key'
                        ? 'animate-pulse border-white/60 bg-white/[0.12] text-white'
                        : 'border-white/12 bg-[#0d0d10] text-[#f4f4f6] hover:border-white/35'
                    }`}
                  >
                    {capturingField === 'ptt_key'
                      ? 'Press new key (e.g. Right Ctrl, F9)...'
                      : formatHotkeyLabel(config.ptt_key)}
                  </button>
                </div>

                <div className="space-y-2">
                  <label className="block text-[11.5px] text-[#9898a4]">
                    Toggle shortcut (press once to start, again to stop)
                  </label>
                  <button
                    type="button"
                    onClick={() => startCapture('toggle_hotkey')}
                    className={`w-full cursor-pointer rounded-xl border px-3.5 py-2.5 text-left font-mono-tech text-[12px] transition ${
                      capturingField === 'toggle_hotkey'
                        ? 'animate-pulse border-white/60 bg-white/[0.12] text-white'
                        : 'border-white/12 bg-[#0d0d10] text-[#f4f4f6] hover:border-white/35'
                    }`}
                  >
                    {capturingField === 'toggle_hotkey'
                      ? 'Press combo (e.g. Ctrl+Shift+Space)...'
                      : formatHotkeyLabel(config.toggle_hotkey)}
                  </button>
                </div>

                <div className="space-y-2">
                  <label className="block text-[11.5px] text-[#9898a4]">Input Microphone</label>
                  <select
                    value={config.device_index === null ? '' : String(config.device_index)}
                    onChange={(e) =>
                      updateConfig({
                        device_index: e.target.value === '' ? null : Number(e.target.value),
                      })
                    }
                    className="w-full rounded-xl border border-white/12 bg-[#0d0d10] px-3 py-2.5 text-[12.5px] text-[#f4f4f6] outline-none focus:border-white/35"
                  >
                    <option value="">Windows Default Microphone</option>
                    {devices.map((d) => (
                      <option key={d.index} value={d.index}>
                        {d.name} {d.isDefault ? '(Default)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="block text-[11.5px] text-[#a1a5b3]">Language Profile</label>
                  <select
                    value={config.language_mode}
                    onChange={(e) =>
                      updateConfig({
                        language_mode: e.target.value as AppConfigState['language_mode'],
                      })
                    }
                    className="w-full rounded-xl border border-white/12 bg-[#0b0d12] px-3 py-2.5 text-[12.5px] text-[#f4f2ed] outline-none"
                  >
                    <option value="az-tech">Azerbaijani + Tech English (Recommended)</option>
                    <option value="az">Azerbaijani Only</option>
                    <option value="en">English Only</option>
                    <option value="auto">Auto Detect</option>
                  </select>
                </div>
              </SpotlightCard>

              {/* Behavior & API Keys */}
              <SpotlightCard className="space-y-4 p-5">
                <h3 className="font-display text-[15px] font-semibold">Injection & API Keys</h3>

                <div className="space-y-2">
                  <label className="block text-[11.5px] text-[#a1a5b3]">Text Injection Method</label>
                  <select
                    value={config.typing_mode}
                    onChange={(e) =>
                      updateConfig({
                        typing_mode: e.target.value as AppConfigState['typing_mode'],
                      })
                    }
                    className="w-full rounded-xl border border-white/12 bg-[#0b0d12] px-3 py-2.5 text-[12.5px] text-[#f4f2ed] outline-none"
                  >
                    <option value="smart">Smart (Short = Direct Unicode, Long = Paste-Restore)</option>
                    <option value="unicode">Direct Keyboard Only (Zero Clipboard)</option>
                    <option value="paste">Instant Paste (Preserves Previous Clipboard)</option>
                  </select>
                </div>

                {[
                  {
                    key: 'auto_enter',
                    label: 'Press Enter automatically after typing',
                    val: config.auto_enter,
                  },
                  {
                    key: 'autostart',
                    label: 'Launch minimized on Windows startup',
                    val: config.autostart,
                  },
                  {
                    key: 'sound_cue',
                    label: 'Play subtle audio cue on start / stop',
                    val: config.sound_cue,
                  },
                ].map((tog) => (
                  <button
                    key={tog.key}
                    type="button"
                    onClick={() => updateConfig({ [tog.key]: !tog.val })}
                    className="flex w-full cursor-pointer items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-3.5 py-2.5 text-[12.5px]"
                  >
                    <span className="text-[#f4f2ed]">{tog.label}</span>
                    <span
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                        tog.val ? 'bg-[#f4f4f6]' : 'bg-white/15'
                      }`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full transition ${
                          tog.val ? 'translate-x-4.5 bg-[#0a0a0b]' : 'translate-x-1 bg-[#9898a4]'
                        }`}
                      />
                    </span>
                  </button>
                ))}

                <div className="space-y-2 border-t border-white/8 pt-3">
                  <div className="flex items-center justify-between text-[11.5px] text-[#9898a4]">
                    <span className="flex items-center gap-1.5">
                      <KeyRound className="h-3.5 w-3.5 text-[#f4f4f6]" />
                      Gemini API Keys ({config.apiKeyCount} failover configured)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {config.apiKeyPreviews.map((p, i) => (
                      <span
                        key={`${p}-${i}`}
                        className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 font-mono-tech text-[10px] text-[#9898a4]"
                      >
                        #{i + 1} {p}
                      </span>
                    ))}
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault()
                      if (!apiKeyDraft.trim()) return
                      updateConfig({ add_api_key: apiKeyDraft.trim() })
                      setApiKeyDraft('')
                    }}
                    className="flex gap-2"
                  >
                    <input
                      value={apiKeyDraft}
                      onChange={(e) => setApiKeyDraft(e.target.value)}
                      placeholder="Add Gemini API key..."
                      className="flex-1 rounded-xl border border-white/12 bg-[#0d0d10] px-3 py-2 font-mono-tech text-[11px] text-[#f4f4f6] placeholder-[#5c5c66] outline-none focus:border-white/35"
                    />
                    <button
                      type="submit"
                      className="cursor-pointer rounded-xl border border-white/25 bg-white/[0.08] px-3 py-2 text-[11.5px] font-semibold text-[#f4f4f6] transition hover:bg-white/[0.15]"
                    >
                      Add
                    </button>
                  </form>
                </div>
              </SpotlightCard>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Bottom macOS-Style ReactBits Dock */}
      <footer className="pointer-events-none fixed bottom-4 left-0 right-0 z-30 flex justify-center">
        <div className="pointer-events-auto">
          <MacDock items={dockItems} activeId={tab} onSelect={(id) => setTab(id as TabId)} />
        </div>
      </footer>
    </div>
  )
}
