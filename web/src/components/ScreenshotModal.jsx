import React from 'react'

export default function ScreenshotModal({ isOpen, onClose, imageUrl, title = 'Captura de Tela do Erro' }) {
  if (!isOpen || !imageUrl) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative max-w-5xl w-full bg-surface border border-edge rounded-xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-3 border-b border-edge bg-raised">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-bad" />
            <h3 className="font-semibold text-sm text-ink">{title}</h3>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={imageUrl}
              download
              target="_blank"
              rel="noreferrer"
              className="btn-secondary text-xs py-1 px-2.5"
            >
              Abrir em Nova Aba
            </a>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-ink-muted hover:text-ink hover:bg-raised transition-all cursor-pointer"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-4 overflow-auto flex items-center justify-center bg-black/20 min-h-[300px]">
          <img
            src={imageUrl}
            alt={title}
            className="max-w-full h-auto rounded border border-white/10 shadow-md object-contain"
          />
        </div>
      </div>
    </div>
  )
}
