import React, { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function TabObservabilidade({ jobs = [], showToast }) {
  const [logSessions, setLogSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [sessionDetail, setSessionDetail] = useState(null)
  const [clearing, setClearing] = useState(false)
  const [clearPassword, setClearPassword] = useState('')
  const [showClearModal, setShowClearModal] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const data = await api.listLogSessions()
      setLogSessions(data || [])
      if (data && data.length > 0 && !selectedSessionId) {
        setSelectedSessionId(data[0].id)
        loadSessionDetail(data[0].id)
      }
    } catch (e) {}
  }

  const loadSessionDetail = async (id) => {
    try {
      const data = await api.getLogSession(id)
      setSessionDetail(data)
    } catch (e) {}
  }

  const handleSelectSession = (id) => {
    setSelectedSessionId(id)
    loadSessionDetail(id)
  }

  const handleExecuteCleanup = async () => {
    if (!clearPassword) {
      showToast('Digite a senha de administrador.', 'warning')
      return
    }
    setClearing(true)
    try {
      await api.clearLogs(clearPassword)
      showToast('Limpeza de logs e artefatos concluída com sucesso!', 'success')
      setShowClearModal(false)
      setClearPassword('')
      loadSessions()
    } catch (e) {
      showToast(`Erro na limpeza: ${e.message}`, 'error')
    } finally {
      setClearing(false)
    }
  }

  // Cálculos de KPIs Globais
  const totalJobs = jobs.length
  const totalItems = jobs.reduce((acc, j) => acc + (j.total_items || 0), 0)
  const totalSuccess = jobs.reduce((acc, j) => acc + (j.success_count || 0), 0)
  const totalErrors = jobs.reduce((acc, j) => acc + (j.error_count || 0), 0)
  const globalSuccessRate = totalItems > 0 ? Math.round((totalSuccess / totalItems) * 100) : 100

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-[var(--text-main)] flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            Painel de Observabilidade & Administração
          </h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Métricas de confiabilidade, integridade do SQLite, logs de auditoria e retenção de mídias
          </p>
        </div>

        <button
          onClick={() => setShowClearModal(true)}
          className="btn-danger text-xs py-1.5 px-3"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          Limpeza de Artefatos & Logs
        </button>
      </div>

      {/* Grid de KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card-panel p-4">
          <span className="text-xs text-[var(--text-muted)] font-semibold uppercase">Total de Lotes</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-[var(--text-main)]">{totalJobs}</span>
            <span className="text-xs text-[var(--text-muted)] font-mono">lotes executados</span>
          </div>
        </div>

        <div className="card-panel p-4">
          <span className="text-xs text-[var(--text-muted)] font-semibold uppercase">CTEs Emitidos</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-emerald-500">{totalSuccess}</span>
            <span className="text-xs text-[var(--text-muted)] font-mono">de {totalItems} total</span>
          </div>
        </div>

        <div className="card-panel p-4">
          <span className="text-xs text-[var(--text-muted)] font-semibold uppercase">Taxa Global de Sucesso</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-[var(--color-primary)]">{globalSuccessRate}%</span>
            <span className="text-xs text-emerald-500">alta confiabilidade</span>
          </div>
        </div>

        <div className="card-panel p-4">
          <span className="text-xs text-[var(--text-muted)] font-semibold uppercase">Total de Falhas</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-red-500">{totalErrors}</span>
            <span className="text-xs text-[var(--text-muted)] font-mono">com foto anexada</span>
          </div>
        </div>
      </div>

      {/* Seção de Sessões de Logs do Servidor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Lista de Sessões */}
        <div className="lg:col-span-4 card-panel p-4 flex flex-col">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)] mb-3 pb-2 border-b border-[var(--border-subtle)]">
            Sessões de Execução
          </h3>

          <div className="flex-1 overflow-y-auto max-h-[420px] space-y-2">
            {logSessions.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)] italic text-center py-6">
                Nenhuma sessão encontrada.
              </p>
            ) : (
              logSessions.map((sess) => (
                <div
                  key={sess.id}
                  onClick={() => handleSelectSession(sess.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedSessionId === sess.id
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                      : 'border-[var(--border-subtle)] bg-[var(--bg-card-secondary)]/50 hover:bg-[var(--bg-card-secondary)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[var(--text-main)] truncate max-w-[150px]">
                      {sess.id}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">
                      {sess.total_logs} logs
                    </span>
                  </div>
                  <span className="text-[11px] text-[var(--text-muted)] block mt-1 truncate">
                    {sess.created_at ? new Date(sess.created_at).toLocaleString('pt-BR') : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Detalhes dos Logs da Sessão */}
        <div className="lg:col-span-8 card-panel p-4 flex flex-col">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)] mb-3 pb-2 border-b border-[var(--border-subtle)]">
            Auditoria da Sessão: {selectedSessionId || 'Nenhuma selecionada'}
          </h3>

          <div className="flex-1 overflow-y-auto max-h-[420px] bg-[var(--terminal-bg)] rounded-lg p-3 font-mono text-xs text-slate-300 space-y-1">
            {!sessionDetail?.logs || sessionDetail.logs.length === 0 ? (
              <p className="text-slate-500 italic py-8 text-center">
                Selecione uma sessão ao lado para inspecionar os logs do servidor.
              </p>
            ) : (
              sessionDetail.logs.map((log, idx) => (
                <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-white/5">
                  <span className="text-slate-500 text-[10px] shrink-0">
                    {log.created_at ? new Date(log.created_at).toLocaleTimeString('pt-BR') : ''}
                  </span>
                  <span className="text-sky-400 font-bold shrink-0">
                    [{log.level || 'INFO'}]
                  </span>
                  <span className="break-all flex-1 text-slate-200">
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Modal de Confirmação de Limpeza de Logs */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="max-w-md w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-2xl">
            <h3 className="text-base font-bold text-red-500 mb-2 flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              Confirmar Limpeza de Artefatos & Logs
            </h3>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Esta ação removerá logs antigos e arquivos temporários de traces. Digite a senha administrativa para prosseguir:
            </p>

            <input
              type="password"
              placeholder="Senha de administrador"
              value={clearPassword}
              onChange={(e) => setClearPassword(e.target.value)}
              className="input-field text-xs font-mono mb-4"
            />

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setShowClearModal(false)}
                className="btn-secondary text-xs"
              >
                Cancelar
              </button>
              <button
                onClick={handleExecuteCleanup}
                disabled={clearing}
                className="btn-danger text-xs"
              >
                {clearing ? 'Limpando...' : 'Executar Limpeza'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
