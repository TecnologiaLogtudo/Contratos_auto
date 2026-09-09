import React, { useEffect, useMemo, useRef, useState } from 'react'

export default function TerminalLogs({ logs = [], isLive = true }) {
  const [filterLevel, setFilterLevel] = useState('TODOS')
  const [searchTerm, setSearchTerm] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef(null)
  const containerRef = useRef(null)

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchLevel = filterLevel === 'TODOS' || (log.level || 'INFO').toUpperCase() === filterLevel.toUpperCase()
      const matchSearch =
        !searchTerm ||
        (log.message && log.message.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (log.nro_cotacao && log.nro_cotacao.includes(searchTerm))
      return matchLevel && matchSearch
    })
  }, [logs, filterLevel, searchTerm])

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [filteredLogs, autoScroll])

  const getLevelColor = (level) => {
    switch ((level || 'INFO').toUpperCase()) {
      case 'SUCESSO':
        return 'text-ok bg-ok-dim border-ok-edge'
      case 'ERRO':
        return 'text-bad bg-bad-dim border-bad-edge'
      case 'AVISO':
        return 'text-warn bg-warn-dim border-warn-edge'
      case 'DEBUG':
        return 'text-ink-dim bg-raised border-edge'
      case 'FASE':
        return 'text-info bg-info-dim border-info-edge'
      default:
        return 'text-info bg-info-dim border-info-edge'
    }
  }

  const copyAllLogs = () => {
    const text = logs.map((l) => `[${l.timestamp || ''}] [${l.level || 'INFO'}] ${l.message}`).join('\n')
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="flex flex-col h-full bg-terminal border border-edge rounded-lg overflow-hidden shadow-lg">
      {/* Header do Terminal */}
      <div className="flex flex-wrap items-center justify-between px-3.5 py-2.5 bg-black/30 border-b border-white/10 gap-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 mr-2">
            <span className="w-2.5 h-2.5 rounded-full bg-bad/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-warn/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-ok/80" />
          </div>
          <span className="font-mono text-xs font-semibold text-ink-muted flex items-center gap-1.5">
            Console de Execução
            {isLive && (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-ok-dim text-ok border border-ok-edge animate-pulse">
                AO VIVO
              </span>
            )}
          </span>
        </div>

        {/* Controles do Terminal */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Filtrar log..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-2 py-1 text-xs rounded bg-black/40 border border-edge text-ink placeholder-ink-dim focus:outline-none focus:border-accent w-28 sm:w-36"
          />

          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="px-2 py-1 text-xs rounded bg-black/40 border border-edge text-ink-muted focus:outline-none focus:border-accent font-mono cursor-pointer"
          >
            <option value="TODOS">TODOS</option>
            <option value="INFO">INFO</option>
            <option value="SUCESSO">SUCESSO</option>
            <option value="AVISO">AVISO</option>
            <option value="ERRO">ERRO</option>
          </select>

          <button
            onClick={() => setAutoScroll((prev) => !prev)}
            title={autoScroll ? 'Pausar Rolagem Automática' : 'Ativar Rolagem Automática'}
            className={`p-1.5 rounded text-xs border transition-all cursor-pointer ${
              autoScroll
                ? 'bg-accent-dim border-accent-edge text-accent'
                : 'bg-black/40 border-edge text-ink-dim'
            }`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14" />
              <path d="m19 12-7 7-7-7" />
            </svg>
          </button>

          <button
            onClick={copyAllLogs}
            title="Copiar todos os logs"
            className="p-1.5 rounded text-xs bg-black/40 border border-edge text-ink-dim hover:text-ink transition-all cursor-pointer"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Corpo de Linhas de Log */}
      <div
        ref={containerRef}
        className="flex-1 p-3 overflow-y-auto font-mono text-xs text-[var(--terminal-text)] space-y-1 select-text min-h-[280px] max-h-[480px]"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-ink-dim italic py-8 text-center">
            Nenhum evento registrado no console até o momento.
          </div>
        ) : (
          filteredLogs.map((log, i) => {
            const timeStr = log.timestamp
              ? new Date(log.timestamp).toLocaleTimeString('pt-BR')
              : ''

            return (
              <div
                key={log.id || i}
                className="flex items-start gap-2 py-0.5 leading-relaxed hover:bg-white/5 px-1 rounded transition-colors group"
              >
                {timeStr && (
                  <span className="text-ink-dim select-none text-[11px] shrink-0">
                    {timeStr}
                  </span>
                )}
                <span
                  className={`px-1.5 py-0.5 rounded border text-[10px] font-bold shrink-0 ${getLevelColor(
                    log.level
                  )}`}
                >
                  {log.level || 'INFO'}
                </span>
                {log.nro_cotacao && (
                  <span className="text-accent font-semibold shrink-0">
                    [{log.nro_cotacao}]
                  </span>
                )}
                <span className="break-all text-ink flex-1">
                  {log.message}
                </span>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
