import React from 'react'
import { motion } from 'framer-motion'

interface BlurTextProps {
  text: string
  className?: string
  delay?: number
  animateBy?: 'words' | 'chars'
}

/** ReactBits-style BlurText: springs each word/character from blurred+offset into crisp focus. */
export const BlurText: React.FC<BlurTextProps> = ({
  text,
  className = '',
  delay = 0.035,
  animateBy = 'words',
}) => {
  const tokens = animateBy === 'words' ? text.split(/(\s+)/) : text.split('')

  return (
    <span className={`inline-flex flex-wrap items-baseline ${className}`}>
      {tokens.map((tok, idx) => {
        if (/^\s+$/.test(tok)) {
          return <span key={`sp-${idx}`}>&nbsp;</span>
        }
        return (
          <motion.span
            key={`${tok}-${idx}`}
            initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{
              duration: 0.42,
              delay: idx * delay,
              ease: [0.22, 1, 0.36, 1],
            }}
            className="inline-block will-change-transform"
          >
            {tok}
          </motion.span>
        )
      })}
    </span>
  )
}
