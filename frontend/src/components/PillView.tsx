import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, Check, Loader2 } from 'lucide-react'
import { AppSnapshot } from '../types'
import { BlurText } from './reactbits/BlurText'

interface PillViewProps {
  snapshot: AppSnapshot
  rms: number
  bands: number[]
}

/** Frameless non-focus-stealing monochrome floating voice capsule over active windows. */
export const PillView: React.FC<PillViewProps> = ({ snapshot, rms, bands }) => {
  const { status, interimText, lastTargetApp, lastText, lastError } = snapshot
  const visible = status !== 'idle'
  const shortTarget = (lastTargetApp || 'Active Window').slice(0, 22)
  const previewInterim = (interimText || '').trim()

  return (
    <div className="flex h-full w-full items-center justify-center bg-transparent px-4">
      <AnimatePresence mode="wait">
        {visible ? (
          <motion.div
            key={status}
            layout
            initial={{ opacity: 0, y: 16, scale: 0.9, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: 12, scale: 0.92, filter: 'blur(6px)' }}
            transition={{ type: 'spring', stiffness: 420, damping: 28 }}
            className={`relative flex min-w-[310px] max-w-[430px] items-center gap-3.5 overflow-hidden rounded-full border px-4 py-2.5 backdrop-blur-2xl shadow-[0_14px_36px_rgba(0,0,0,0.72)] ${
              status === 'error'
                ? 'border-white/25 bg-[#161213]/96'
                : 'border-white/22 bg-[#101013]/96'
            }`}
          >
            {status === 'recording' ? (
              <>
                <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.08]">
                  <motion.span
                    animate={{ scale: [1, 1.3 + rms * 0.35, 1] }}
                    transition={{ duration: 0.9, repeat: Infinity }}
                    className="h-2.5 w-2.5 rounded-full bg-[#f4f4f6]"
                  />
                </div>
                <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
                  <div className="flex items-center gap-2">
                    <span className="shrink-0 text-[12px] font-semibold text-[#f4f4f6]">
                      Listening
                    </span>
                    <span className="truncate font-mono-tech text-[10px] text-[#9898a4]">
                      {previewInterim ? previewInterim.slice(-34) : `→ ${shortTarget}`}
                    </span>
                  </div>
                  <div className="flex h-4 items-center gap-[3px]">
                    {Array.from({ length: 14 }).map((_, i) => {
                      const val = Math.max(0.12, bands[i] ?? rms)
                      return (
                        <motion.span
                          key={i}
                          animate={{ height: 3 + val * 14 }}
                          transition={{ type: 'spring', stiffness: 480, damping: 24 }}
                          className="w-[3px] rounded-full bg-[#e4e4e8]"
                        />
                      )
                    })}
                  </div>
                </div>
              </>
            ) : status === 'transcribing' ? (
              <>
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/12 bg-white/[0.06] text-[#f4f4f6]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <div className="flex flex-1 flex-col">
                  <span className="shiny-text text-[13px] font-semibold">
                    Finalizing transcript...
                  </span>
                  <span className="truncate font-mono-tech text-[10px] text-[#8d8d99]">
                    {shortTarget}
                  </span>
                </div>
              </>
            ) : status === 'error' ? (
              <>
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.08] text-[#d4d4d8]">
                  <AlertCircle className="h-4 w-4" />
                </div>
                <span className="truncate text-[12px] font-medium text-[#e4e4e8]">
                  {lastError || 'An error occurred'}
                </span>
              </>
            ) : (
              <>
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#f4f4f6] text-[#0a0a0b]">
                  <Check className="h-4 w-4 stroke-[2.6]" />
                </div>
                <div className="min-w-0 flex-1">
                  <BlurText
                    text={lastText.length > 52 ? `${lastText.slice(0, 52)}…` : lastText || 'Inserted'}
                    delay={0.025}
                    className="text-[12.5px] font-medium text-[#f4f4f6]"
                  />
                </div>
              </>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
