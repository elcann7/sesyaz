import React, { useRef, useState } from 'react'
import {
  AnimatePresence,
  MotionValue,
  motion,
  useMotionValue,
  useSpring,
  useTransform,
} from 'framer-motion'

export interface DockItemData {
  id: string
  label: string
  icon: React.ReactNode
  badge?: number
}

interface DockIconProps {
  item: DockItemData
  active: boolean
  mouseX: MotionValue<number>
  onClick: () => void
}

const DockIconButton: React.FC<DockIconProps> = ({ item, active, mouseX, onClick }) => {
  const ref = useRef<HTMLButtonElement>(null)
  const [hovered, setHovered] = useState(false)

  const distance = useTransform(mouseX, (val) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect || val === Infinity) return 200
    return val - (rect.left + rect.width / 2)
  })

  const sizeSync = useTransform(distance, [-120, 0, 120], [42, 56, 42])
  const size = useSpring(sizeSync, { mass: 0.12, stiffness: 240, damping: 18 })

  return (
    <motion.button
      ref={ref}
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ width: size, height: size }}
      whileTap={{ scale: 0.92 }}
      className={`relative flex cursor-pointer items-center justify-center rounded-xl border transition-colors ${
        active
          ? 'border-white/35 bg-white/[0.12] text-[#f4f4f6]'
          : 'border-white/[0.08] bg-white/[0.03] text-[#8d8d99] hover:border-white/20 hover:text-[#f4f4f6]'
      }`}
    >
      {item.icon}
      {item.badge ? (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#f4f4f6] px-1 text-[10px] font-bold text-[#0a0a0b]">
          {item.badge > 99 ? '99+' : item.badge}
        </span>
      ) : null}
      {active ? (
        <motion.span
          layoutId="dock-active-dot"
          className="absolute -bottom-1.5 h-[3px] w-4 rounded-full bg-[#f4f4f6]"
          transition={{ type: 'spring', stiffness: 360, damping: 28 }}
        />
      ) : null}
      <AnimatePresence>
        {hovered ? (
          <motion.span
            initial={{ opacity: 0, y: 6, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.92 }}
            transition={{ duration: 0.14 }}
            className="pointer-events-none absolute -top-9 whitespace-nowrap rounded-md border border-white/15 bg-[#16161a] px-2.5 py-1 text-[11px] font-medium text-[#f4f4f6] shadow-md"
          >
            {item.label}
          </motion.span>
        ) : null}
      </AnimatePresence>
    </motion.button>
  )
}

interface MacDockProps {
  items: DockItemData[]
  activeId: string
  onSelect: (id: string) => void
}

/** Monochrome macOS magnification Dock navigation bar. */
export const MacDock: React.FC<MacDockProps> = ({ items, activeId, onSelect }) => {
  const mouseX = useMotionValue(Infinity)

  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.clientX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className="flex h-[58px] items-end gap-2.5 rounded-2xl border border-white/[0.11] bg-[#111114]/94 px-3 pb-2 backdrop-blur-2xl shadow-[0_14px_34px_rgba(0,0,0,0.65)]"
    >
      {items.map((item) => (
        <DockIconButton
          key={item.id}
          item={item}
          active={item.id === activeId}
          mouseX={mouseX}
          onClick={() => onSelect(item.id)}
        />
      ))}
    </motion.div>
  )
}
