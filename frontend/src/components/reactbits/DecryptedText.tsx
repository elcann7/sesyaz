import React, { useEffect, useState } from 'react'

const SCRAMBLE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789əşğçöüı'

interface DecryptedTextProps {
  text: string
  className?: string
  speedMs?: number
}

/** ReactBits-style DecryptedText: cycles random glyphs into the settled transcription text. */
export const DecryptedText: React.FC<DecryptedTextProps> = ({
  text,
  className = '',
  speedMs = 18,
}) => {
  const [rendered, setRendered] = useState(text)

  useEffect(() => {
    if (!text) {
      setRendered('')
      return
    }
    let frame = 0
    const total = Math.min(22, Math.max(8, Math.ceil(text.length * 0.45)))
    const timer = window.setInterval(() => {
      frame += 1
      const progress = frame / total
      const revealCount = Math.floor(progress * text.length)
      const next = text
        .split('')
        .map((ch, i) => {
          if (ch === ' ' || ch === '\n' || i < revealCount) return ch
          return SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)]
        })
        .join('')
      setRendered(next)
      if (frame >= total) {
        setRendered(text)
        window.clearInterval(timer)
      }
    }, speedMs)

    return () => window.clearInterval(timer)
  }, [text, speedMs])

  return <span className={className}>{rendered}</span>
}
