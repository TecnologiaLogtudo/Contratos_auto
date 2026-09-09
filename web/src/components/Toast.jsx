import React, { useEffect } from 'react'

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => {
      onClose()
    }, 4500)
    return () => clearTimeout(timer)
  }, [toast, onClose])

  if (!toast) return null

  const getStyle = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-ok-dim text-ok border-ok-edge'
      case 'error':
        return 'bg-bad-dim text-bad border-bad-edge'
      case 'warning':
        return 'bg-warn-dim text-warn border-warn-edge'
      default:
        return 'bg-accent-dim text-accent border-accent-edge'
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 animate-slideUp">
      <div
        className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl backdrop-blur-md text-sm font-medium ${getStyle()}`}
      >
        <span>{toast.message}</span>
        <button
          onClick={onClose}
          className="p-1 hover:opacity-80 transition-opacity cursor-pointer"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  )
}
