import React, { useEffect, useState } from 'react'

interface CountUpProps {
  to: number
  durationMs?: number
  decimals?: number
  className?: string
}

/** ReactBits-style CountUp: smooth ease-out cubic counter for telemetry numbers. */
export const CountUp: React.FC<CountUpProps> = ({
  to,
  durationMs = 700,
  decimals = 0,
  className = '',
}) => {
  const [val, setVal] = useState(0)

  useEffect(() => {
    let raf = 0
    const startVal = val
    const startTime = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - startTime) / durationMs)
      const eased = 1 - Math.pow(1 - p, 3)
      setVal(startVal + (to - startVal) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to])

  return <span className={className}>{val.toFixed(decimals)}</span>
}
