import React, { useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

interface MagnetProps {
  children: React.ReactNode
  padding?: number
  strength?: number
  disabled?: boolean
  className?: string
}

/** ReactBits-style Magnet: elastic spring pull toward the pointer within range. */
export const Magnet: React.FC<MagnetProps> = ({
  children,
  padding = 42,
  strength = 0.28,
  disabled = false,
  className = '',
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x = useSpring(rawX, { stiffness: 260, damping: 18, mass: 0.45 })
  const y = useSpring(rawY, { stiffness: 260, damping: 18, mass: 0.45 })

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (disabled || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = e.clientX - cx
    const dy = e.clientY - cy
    if (Math.abs(dx) < rect.width / 2 + padding && Math.abs(dy) < rect.height / 2 + padding) {
      rawX.set(dx * strength)
      rawY.set(dy * strength)
    }
  }

  const reset = () => {
    rawX.set(0)
    rawY.set(0)
  }

  return (
    <motion.div
      ref={ref}
      style={{ x, y }}
      onMouseMove={handleMove}
      onMouseLeave={reset}
      className={`inline-block ${className}`}
    >
      {children}
    </motion.div>
  )
}
