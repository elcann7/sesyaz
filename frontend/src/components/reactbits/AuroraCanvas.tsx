import React, { useEffect, useRef } from 'react'

interface AuroraCanvasProps {
  active: boolean
  rms: number
}

/** Subtle monochrome architectural vignette & micro-dot surface (zero colored glow). */
export const AuroraCanvas: React.FC<AuroraCanvasProps> = ({ active, rms }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rmsRef = useRef(rms)
  const activeRef = useRef(active)
  rmsRef.current = rms
  activeRef.current = active

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let t = 0

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = canvas.clientWidth * dpr
      canvas.height = canvas.clientHeight * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const draw = () => {
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      const boost = activeRef.current ? 0.25 + rmsRef.current * 1.1 : 0.05
      t += 0.005 + boost * 0.01

      ctx.clearRect(0, 0, w, h)

      // Neutral top-center studio key light falloff (grayscale only)
      const cx = w * (0.5 + Math.sin(t * 0.5) * 0.06)
      const cy = h * 0.14
      const g = ctx.createRadialGradient(cx, cy, 10, cx, cy, w * 0.58)
      const peakAlpha = activeRef.current ? 0.055 + rmsRef.current * 0.045 : 0.035
      g.addColorStop(0, `rgba(255, 255, 255, ${peakAlpha})`)
      g.addColorStop(0.55, 'rgba(180, 180, 190, 0.015)')
      g.addColorStop(1, 'rgba(10, 10, 11, 0)')
      ctx.fillStyle = g
      ctx.fillRect(0, 0, w, h)

      // Precision architectural dot matrix
      const step = 28
      const dotAlpha = activeRef.current ? 0.06 + rmsRef.current * 0.06 : 0.038
      ctx.fillStyle = `rgba(244, 244, 246, ${dotAlpha})`
      for (let x = 14; x < w; x += step) {
        for (let y = 14; y < h; y += step) {
          ctx.fillRect(x, y, 1, 1)
        }
      }

      raf = requestAnimationFrame(draw)
    }

    raf = requestAnimationFrame(draw)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 h-full w-full" />
}
