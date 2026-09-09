import React from 'react'
import { useTheme } from '../context/ThemeContext'
import { api } from '../services/api'

export default function Sidebar({
  activeTab,
  setActiveTab,
  isConnected,
  currentJob,
  isProcessing,
  isPaused,
  progress,
  activeItem,
  onGoToJob,
}) {
  const { theme, toggleTheme } = useTheme()

  const navItems = [
    { id: 'emissao', label: 'Emissão de CTes' },
    { id: 'historico', label: 'Histórico' },
    { id: 'admin', label: 'Admin' },
  ]

  const jobStatus = currentJob?.status || null
  const isRunning = jobStatus === 'RUNNING'
  const isPausedSt = jobStatus === 'PAUSED'
  const pct = Math.round((progress || 0) * 100)
  const done = currentJob?.success_count || 0
  const total = currentJob?.total_items || 0

  return (
    <aside className="w-64 shrink-0 border-r border-edge bg-surface flex flex-col h-screen sticky top-0">
      {/* Marca */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-edge">
        <img
          src="/brand/logos/logo_logtudo.png"
          alt="LogTudo"
          className="h-8 w-auto object-contain"
          onError={(e) => (e.target.style.display = 'none')}
        />
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-sm text-ink">
            LogTudo <span className="text-accent">Contratos</span>
          </span>
          <span className="text-[10px] font-mono text-ink-dim tracking-wider">AUTOMAÇÃO v2.0</span>
        </div>
      </div>

      {/* Navegação */}
      <nav className="px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
          >
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Mini-card do job ativo — sempre visível */}
      <div className="px-3 mt-2">
        <div
          onClick={onGoToJob}
          className={`rounded-lg border p-3 cursor-pointer transition-colors ${
            hasJobActivity(currentJob, isProcessing)
              ? 'border-accent/40 bg-accent-soft'
              : 'border-edge bg-raised hover:border-edge-strong'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
              Lote Ativo
            </span>
            {hasJobActivity(currentJob, isProcessing) && (
              <span className={`w-2 h-2 rounded-full pulse-dot ${isPausedSt ? 'bg-warn' : 'bg-ok'}`} />
            )}
          </div>

          {currentJob ? (
            <>
              <p className="font-mono text-xs font-semibold text-ink truncate" title={currentJob.id}>
                {shortId(currentJob.id)}
              </p>

              <div className="flex items-baseline justify-between mt-1.5">
                <span className="font-mono text-[11px] text-ink-muted">
                  {done}/{total}
                </span>
                <span className="font-mono text-[11px] font-bold text-accent">{pct}%</span>
              </div>
              <div className="progress-track mt-1" style={{ height: 4 }}>
                <div className="progress-fill" style={{ width: `${pct}%` }} />
              </div>

              {/* Cotação em processamento */}
              <div className="mt-2 pt-2 border-t border-edge">
                <span className="text-[10px] text-ink-dim uppercase tracking-wider">Processando</span>
                <p className="font-mono text-[11px] text-ink truncate mt-0.5">
                  {activeItem?.nro_cotacao || '—'}
                </p>
              </div>

              {/* Status textual */}
              <div className="mt-2">
                <span
                  className={`pill ${
                    isRunning ? 'pill-success' : isPausedSt ? 'pill-warning' : 'pill-muted'
                  }`}
                >
                  {isRunning ? 'Executando' : isPausedSt ? 'Pausado' : statusLabel(jobStatus)}
                </span>
              </div>
            </>
          ) : (
            <p className="text-[11px] text-ink-dim italic">Nenhum lote em andamento</p>
          )}
        </div>
      </div>

      {/* Rodapé: status + tema */}
      <div className="mt-auto px-3 pb-4 space-y-2">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-raised border border-edge">
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isConnected ? 'bg-ok' : 'bg-warn pulse-dot'
            }`}
          />
          <span className="text-[11px] text-ink-muted truncate">
            {isConnected ? 'Sistema pronto' : 'Reconectando…'}
          </span>
        </div>

        <button
          onClick={toggleTheme}
          className="nav-item justify-center border border-edge"
          title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}
        >
          {theme === 'dark' ? '☾ Tema escuro' : '☀ Tema claro'}
        </button>
      </div>
    </aside>
  )
}

function hasJobActivity(job, isProcessing) {
  return isProcessing || job?.status === 'RUNNING' || job?.status === 'PAUSED'
}

function shortId(id = '') {
  // job_20260908_145338_c30cb4 -> 08/09 14:53 c30cb4
  const m = id.match(/job_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}_(\w+)/)
  if (m) return `${m[3]}/${m[2]} ${m[4]}:${m[5]} · ${m[6]}`
  return id
}

function statusLabel(status) {
  const map = {
    COMPLETED: 'Concluído',
    FAILED: 'Falhou',
    CANCELLED: 'Cancelado',
    PENDING: 'Aguardando',
  }
  return map[status] || status || '—'
}
