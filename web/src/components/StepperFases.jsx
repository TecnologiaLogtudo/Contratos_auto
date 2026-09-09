import React from 'react'

const FASES = [
  { id: 'F1', title: 'Leitura', subtitle: 'Sanitização Excel' },
  { id: 'F2', title: 'Login', subtitle: 'Sessão e-Login' },
  { id: 'F3', title: 'Cotação', subtitle: 'Busca & Extração' },
  { id: 'F4', title: 'Frete', subtitle: 'Dados do Motorista' },
  { id: 'F5', title: 'Contrato', subtitle: 'Emissão & Saldo' },
]

export default function StepperFases({ currentPhase = 'F1', activeItem = null }) {
  const currentIndex = Math.max(
    0,
    FASES.findIndex((f) => f.id === (currentPhase?.toUpperCase() || 'F1'))
  )

  return (
    <div className="pt-3 border-t border-edge">
      {/* Cotação em processamento */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3">
        <span className="text-[10px] font-bold uppercase tracking-wider text-ink-dim">
          Cotação em Processamento
        </span>
        <span className="font-mono text-sm font-bold text-accent">
          {activeItem?.nro_cotacao || '—'}
        </span>
        {activeItem?.nome && (
          <span className="text-[11px] text-ink-muted">
            {activeItem.nome} · <span className="font-mono">{activeItem.placa}</span>
          </span>
        )}
      </div>

      {/* Stepper horizontal */}
      <div className="relative flex items-start justify-between w-full">
        <div className="absolute left-5 right-5 top-4 -translate-y-1/2 h-0.5 bg-edge z-0" />
        <div
          className="absolute left-5 top-4 -translate-y-1/2 h-0.5 bg-accent z-0 transition-all duration-500 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, (currentIndex / (FASES.length - 1)) * 100))}%` }}
        />

        {FASES.map((fase, idx) => {
          const isCompleted = idx < currentIndex
          const isCurrent = idx === currentIndex

          return (
            <div key={fase.id} className="relative flex flex-col items-center z-10" style={{ minWidth: 64 }}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-mono font-bold text-[11px] transition-all duration-300 ${
                  isCompleted
                    ? 'bg-accent text-white'
                    : isCurrent
                    ? 'bg-accent text-white ring-4 ring-[var(--color-accent-soft)] scale-110'
                    : 'bg-raised text-ink-dim border border-edge'
                }`}
              >
                {isCompleted ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  fase.id
                )}
              </div>

              <div className="text-center mt-1.5">
                <p className={`text-[11px] font-semibold leading-tight ${isCurrent ? 'text-accent' : isCompleted ? 'text-ink' : 'text-ink-dim'}`}>
                  {fase.title}
                </p>
                <p className="hidden md:block text-[10px] text-ink-dim leading-tight">{fase.subtitle}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
