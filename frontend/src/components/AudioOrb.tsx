import React from 'react'
import { motion } from 'framer-motion'
import { Loader2, Mic, Square } from 'lucide-react'
import { Magnet } from './reactbits/Magnet'

interface AudioOrbProps {
  status: string
  rms: number
  bands: number[]
  onToggle: () => void
}

/** Crisp monochrome acoustic orb with radial 16-band spectrum & magnetic spring physics. */
export const AudioOrb: React.FC<AudioOrbProps> = ({ status, rms, bands, onToggle }) => {
  const isRec = status === 'recording'
  const isBusy = status === 'transcribing'
  const ringScale = isRec ? 1 + rms * 0.2 : 1

  return (
    <div className="relative flex items-center justify-center py-2">
      {/* Hairline concentric acoustic rings during live recording (zero neon blur) */}
      {isRec ? (
        <>
          <motion.div
            animate={{ scale: [1, 1.44], opacity: [0.42, 0] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
            className="pointer-events-none absolute h-32 w-32 rounded-full border border-white/40"
          />
          <motion.div
            animate={{ scale: [1, 1.28], opacity: [0.3, 0] }}
            transition={{ duration: 1.4, delay: 0.5, repeat: Infinity, ease: 'easeOut' }}
            className="pointer-events-none absolute h-32 w-32 rounded-full border border-white/20"
          />
        </>
      ) : null}

      {/* 16 radial precision spectrum ticks around orb */}
      <div className="pointer-events-none absolute h-44 w-44">
        {Array.from({ length: 16 }).map((_, i) => {
          const val = isRec ? Math.max(0.12, bands[i] || rms) : isBusy ? 0.22 : 0.08
          const deg = (i * 360) / 16
          return (
            <div
              key={i}
              style={{
                transform: `rotate(${deg}deg)`,
              }}
              className="absolute inset-0 flex justify-center"
            >
              <motion.div
                animate={{
                  height: 6 + val * 18,
                  opacity: isRec ? 0.45 + val * 0.55 : isBusy ? 0.45 : 0.22,
                }}
                transition={{ type: 'spring', stiffness: 420, damping: 24 }}
                className={`w-[2.5px] rounded-full ${
                  isRec ? 'bg-[#f4f4f6]' : isBusy ? 'bg-[#c4c4cc]' : 'bg-white/25'
                }`}
              />
            </div>
          )
        })}
      </div>

      <Magnet strength={0.28} padding={44}>
        <motion.button
          type="button"
          onClick={onToggle}
          disabled={isBusy}
          animate={{ scale: ringScale }}
          whileHover={{ scale: isRec ? ringScale * 1.03 : 1.04 }}
          whileTap={{ scale: 0.94 }}
          transition={{ type: 'spring', stiffness: 320, damping: 20 }}
          className={`relative flex h-28 w-28 cursor-pointer items-center justify-center rounded-full border transition-colors ${
            isRec
              ? 'border-white bg-[#f4f4f6] text-[#0a0a0b]'
              : isBusy
                ? 'border-white/40 bg-[#1a1a1f] text-[#f4f4f6]'
                : 'border-white/18 bg-[#151519] text-[#f4f4f6] hover:border-white/45 hover:bg-[#1c1c22]'
          }`}
        >
          {isBusy ? (
            <Loader2 className="h-8 w-8 animate-spin" />
          ) : isRec ? (
            <Square className="h-7 w-7 fill-current" />
          ) : (
            <Mic className="h-8 w-8" />
          )}
        </motion.button>
      </Magnet>
    </div>
  )
}
