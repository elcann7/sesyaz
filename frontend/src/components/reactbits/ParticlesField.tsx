import React, { useEffect, useRef } from 'react'

interface ParticlesFieldProps {
  rms: number
  recording: boolean
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  alpha: number
}

/** Monochrome ash-white micro-particles responding subtly to pointer & mic RMS. */
export const ParticlesField: React.FC<ParticlesFieldProps> = ({ rms, recording }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pointerRef = useRef<{ x: number; y: number; active: boolean }>({ x: 0, y: 0, active: false })
  const rmsRef = useRef(rms)
  const recRef = useRef(recording)
  rmsRef.current = rms
  recRef.current = recording

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let w = canvas.clientWidth
    let h = canvas.clientHeight

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const count = 34
    const particles: Particle[] = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      r: 0.8 + Math.random() * 1.1,
      alpha: 0.06 + Math.random() * 0.14,
    }))

    const onMove = (e: MouseEvent) => {
      pointerRef.current = { x: e.clientX, y: e.clientY, active: true }
    }
    const onLeave = () => {
      pointerRef.current.active = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseleave', onLeave)

    const tick = () => {
      ctx.clearRect(0, 0, w, h)
      const speedMult = recRef.current ? 1.3 + rmsRef.current * 3.0 : 1.0
      const ptr = pointerRef.current

      for (const p of particles) {
        if (ptr.active) {
          const dx = p.x - ptr.x
          const dy = p.y - ptr.y
          const dist = Math.hypot(dx, dy)
          if (dist < 100 && dist > 1) {
            const push = (1 - dist / 100) * 0.28
            p.x += (dx / dist) * push
            p.y += (dy / dist) * push
          }
        }
        p.x += p.vx * speedMult
        p.y += p.vy * speedMult

        if (p.x < 0) p.x = w
        if (p.x > w) p.x = 0
        if (p.y < 0) p.y = h
        if (p.y > h) p.y = 0

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        const a = recRef.current ? Math.min(0.42, p.alpha + rmsRef.current * 0.22) : p.alpha
        ctx.fillStyle = `rgba(235, 235, 240, ${a})`
        ctx.fill()
      }

      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseleave', onLeave)
    }
  }, [])

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 h-full w-full" />
}
