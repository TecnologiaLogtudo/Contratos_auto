import React, { useEffect, useMemo, useRef, useState } from 'react'
import StepperFases from './StepperFases'
import TerminalLogs from './TerminalLogs'
import { api } from '../services/api'

export default function TabEmissao({
  config,
  currentJob,
  jobItems = [],
  logs = [],
  activeItem,
  currentPhase,
  isProcessing,
  isPaused,
  hasActiveJob,
  onUploadAndValidate,
  onStartJob,
  onPauseJob,
  onResumeJob,
  onCancelJob,
  preValidationReport,
  onResetPreValidation,
  onOpenScreenshot,
}) {
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [loginInput, setLoginInput] = useState(config?.login || '')
  const [senhaInput, setSenhaInput] = useState(config?.senha || '')
  const [savingCreds, setSavingCreds] = useState(false)
  const [headlessInput, setHeadlessInput] = useState(false)
  const [selectedItem, setSelectedItem] = useState(null)
  const [credsEditing, setCredsEditing] = useState(false)
  const fileInputRef = useRef(null)

  const credsSaved = !!config?.login

  useEffect(() => {
    if (config?.login) setLoginInput(config.login)
  }, [config?.login])

  const handleFile = async (file) => {
    setUploading(true)
    try {
      await onUploadAndValidate(file)
    } finally {
      setUploading(false)
    }
  }

  const handleFileDrop = async (e) => {
    e.preventDefault()
    setDragOver(false)
    const files = e.dataTransfer?.files
    if (files?.length) await handleFile(files[0])
  }

  const handleFileChange = async (e) => {
    const files = e.target.files
    if (files?.length) await handleFile(files[0])
    e.target.value = ''
  }

  const handleSaveCreds = () => {
    setSavingCreds(true)
    try {
      const next = { ...config, login: loginInput, senha: senhaInput }
      localStorage.setItem('logtudo_config', JSON.stringify(next))
      // usa o handler global que persiste no backend também
      window.dispatchEvent(new CustomEvent('logtudo:save-config', { detail: next }))
    } finally {
      setTimeout(() => setSavingCreds(false), 400)
    }
  }

  const handleStart = () => {
    onStartJob(currentJob.id, {
      login: loginInput || config?.login,
      senha: senhaInput || config?.senha,
      headless: headlessInput,
    })
  }

  const done = currentJob?.success_count || 0
  const failed = currentJob?.error_count || 0
  const total = currentJob?.total_items || 0
  const pct = total ? Math.round((done / total) * 100) : 0
  const jobFinished = currentJob && ['COMPLETED', 'FAILED', 'CANCELLED'].includes(currentJob.status)

  // Status do item de validação prévia: linhas com inconsistência vão para Contrato Não Realizado
  const invalidRows = useMemo(() => {
    if (!preValidationReport) return []
    return preValidationReport.invalid_rows || preValidationReport.rows_with_issues || []
  }, [preValidationReport])

  const itemCounts = useMemo(() => {
    const s = { Pendente: 0, 'Em Processamento': 0, Concluído: 0, Erro: 0, outro: 0 }
    for (const it of jobItems) {
      if (it.status in s) s[it.status]++
      else s.outro++
    }
    return s
  }, [jobItems])

  return (
    <div className="space-y-5">
      {/* ============ LINHA 1: Credenciais + Planilha ============ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card Credenciais do ERP */}
        <div className="card-panel p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              Credenciais do ERP
            </h3>
            {credsSaved && !hasActiveJob && (
              <button
                onClick={() => setCredsEditing((v) => !v)}
                className="text-[11px] text-accent hover:underline cursor-pointer"
              >
                {credsEditing ? 'Fechar' : 'Editar'}
              </button>
            )}
          </div>

          {credsSaved && !credsEditing ? (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-raised border border-edge">
              <span className="w-2.5 h-2.5 rounded-full bg-ok shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-ink-muted">Conectado como</p>
                <p className="font-mono text-sm font-semibold text-ink truncate">
                  {config.login}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-ink-muted mb-1">
                  Usuário
                </label>
                <input
                  type="text"
                  value={loginInput}
                  onChange={(e) => setLoginInput(e.target.value)}
                  placeholder="e-login"
                  className="input-field font-mono"
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-ink-muted mb-1">
                  Senha
                </label>
                <input
                  type="password"
                  value={senhaInput}
                  onChange={(e) => setSenhaInput(e.target.value)}
                  placeholder="••••••••"
                  className="input-field font-mono"
                  autoComplete="current-password"
                />
              </div>
              <button
                onClick={handleSaveCreds}
                disabled={savingCreds || !loginInput}
                className="btn btn-primary w-full"
              >
                {savingCreds ? 'Salvando…' : 'Salvar credenciais'}
              </button>
            </div>
          )}
        </div>

        {/* Card Planilha de CTEs */}
        <div className="card-panel p-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted mb-4">
            Planilha de CTEs
          </h3>

          {currentJob || preValidationReport ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-raised border border-edge">
                <FileIcon />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink truncate">
                    {preValidationReport?.filename || currentJob?.filename || 'Planilha carregada'}
                  </p>
                  <p className="font-mono text-[11px] text-ink-muted">
                    {total} linha{total === 1 ? '' : 's'} detectada{total === 1 ? '' : 's'}
                  </p>
                </div>
              </div>

              {/* Validação prévia inline */}
              {preValidationReport && (
                <div className="p-3 rounded-lg border border-warn/30 bg-warn/5">
                  <p className="text-xs font-semibold text-warn mb-1">
                    Validação Prévia do Lote
                  </p>
                  {invalidRows.length > 0 ? (
                    <p className="text-[11px] text-ink-muted">
                      <b className="text-warn">{invalidRows.length}</b> linha
                      {invalidRows.length === 1 ? '' : 's'} com inconsistência — irão para
                      <b className="text-ink"> Contrato Não Realizado</b>.
                    </p>
                  ) : (
                    <p className="text-[11px] text-ok">
                      Nenhuma inconsistência detectada. Lote pronto para execução.
                    </p>
                  )}
                </div>
              )}

              {!hasActiveJob && !jobFinished && (
                <div className="flex gap-2">
                  <button onClick={handleStart} className="btn btn-primary flex-1" disabled={uploading}>
                    Iniciar execução
                  </button>
                  <label className="btn btn-secondary cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={headlessInput}
                      onChange={(e) => setHeadlessInput(e.target.checked)}
                      className="mr-1 accent-[var(--color-accent)]"
                    />
                    Headless
                  </label>
                </div>
              )}

              {jobFinished && (
                <button onClick={onResetPreValidation} className="btn btn-secondary w-full">
                  Carregar nova planilha
                </button>
              )}
            </div>
          ) : (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center py-10 px-4 rounded-lg border-2 border-dashed cursor-pointer transition-colors ${
                  dragOver
                    ? 'border-accent bg-accent-soft'
                    : 'border-edge hover:border-edge-strong bg-app'
                }`}
              >
                {uploading ? (
                  <>
                    <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3" />
                    <p className="text-xs text-ink-muted">Validando planilha…</p>
                  </>
                ) : (
                  <>
                    <UploadIcon />
                    <p className="text-xs text-ink mt-3 font-medium">
                      Arraste a planilha .xlsx aqui ou clique para selecionar
                    </p>
                    <p className="text-[11px] text-ink-dim mt-1">
                      A validação prévia roda automaticamente após o upload
                    </p>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ============ LINHA 2+3: Lote Ativo + Console/Itens (quando há lote) ============ */}
      {currentJob ? (
        <>
          {/* ============ LINHA 2: Lote Ativo ============ */}
          <div className="card-panel p-5">
          {/* Topo: título + controles */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-edge">
            <div className="flex items-center gap-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                Lote Ativo
              </h3>
              <span
                className={`pill ${
                  isProcessing && !isPaused
                    ? 'pill-success'
                    : isPaused
                    ? 'pill-warning'
                    : jobFinished
                    ? currentJob.status === 'COMPLETED'
                      ? 'pill-success'
                      : 'pill-error'
                    : 'pill-primary'
                }`}
              >
                {isProcessing && !isPaused
                  ? 'Executando'
                  : isPaused
                  ? 'Pausado'
                  : jobFinished
                  ? statusLabel(currentJob.status)
                  : 'Pronto'}
              </span>
              <span className="font-mono text-xs text-ink-muted truncate max-w-[240px]" title={currentJob.id}>
                {currentJob.id}
              </span>
            </div>

            {/* Controles */}
            <div className="flex items-center gap-2">
              {isProcessing && !isPaused && (
                <button onClick={onPauseJob} className="btn btn-warning">
                  Pausar
                </button>
              )}
              {isPaused && (
                <button onClick={onResumeJob} className="btn btn-primary">
                  Retomar
                </button>
              )}
              {isProcessing && (
                <button onClick={onCancelJob} className="btn btn-danger">
                  Cancelar
                </button>
              )}
            </div>
          </div>

          {/* Meio: barra de progresso com 12/20 */}
          <div className="py-4">
            <div className="flex items-baseline justify-between mb-2">
              <span className="font-mono text-sm text-ink">
                <b className="text-ink font-bold">{done}</b>
                <span className="text-ink-dim">/{total}</span>
                <span className="text-ink-muted text-xs ml-2">
                  itens ({failed} falha{failed === 1 ? '' : 's'})
                </span>
              </span>
              <span className="font-mono text-lg font-bold text-accent">{pct}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>

          {/* Base: cotação em processamento + stepper */}
          <StepperFases currentPhase={currentPhase} activeItem={activeItem} />
          </div>

          {/* ============ LINHA 3: Console + Tabela de Itens ============ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
            <TerminalLogs logs={logs} isLive={isProcessing && !isPaused} />

            <ItemsTable
              items={jobItems}
              selectedItem={selectedItem}
              onSelect={setSelectedItem}
              activeItem={activeItem}
              onOpenScreenshot={onOpenScreenshot}
            />
          </div>
        </>
      ) : (
        <div className="card-panel p-10 text-center mt-5">
          <p className="text-sm font-semibold text-ink mb-1.5">Nenhum lote em andamento</p>
          <p className="text-xs text-ink-muted max-w-md mx-auto">
            Salve as credenciais do ERP, arraste a planilha .xlsx no card ao lado e a validação prévia
            libera o botão <b className="text-ink">Iniciar execução</b>. O progresso e o console
            aparecerão aqui durante o processamento.
          </p>
        </div>
      )}
    </div>
  )
}

/* ---------- Tabela de Itens do Lote ---------- */
function ItemsTable({ items, selectedItem, onSelect, activeItem, onOpenScreenshot }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('TODOS')

  const filtered = useMemo(() => {
    return items.filter((it) => {
      const matchSearch =
        !search ||
        String(it.nro_cotacao || '').includes(search) ||
        (it.nome || '').toLowerCase().includes(search.toLowerCase()) ||
        (it.placa || '').toUpperCase().includes(search.toUpperCase())
      const matchStatus = statusFilter === 'TODOS' || it.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [items, search, statusFilter])

  return (
    <div className="card-panel flex flex-col overflow-hidden" style={{ maxHeight: 520 }}>
      {/* Header: título + busca + filtro */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-edge">
        <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted shrink-0">
          Itens do Lote
        </h3>
        <div className="flex items-center gap-2 flex-1 justify-end">
          <input
            type="text"
            placeholder="Cotação, motorista, placa…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field text-[11px] py-1 px-2.5 w-40"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-field text-[11px] py-1 px-2 w-28 font-mono"
          >
            <option value="TODOS">TODOS</option>
            <option value="Pendente">Pendente</option>
            <option value="Concluído">Concluído</option>
            <option value="Erro">Erro</option>
          </select>
        </div>
      </div>

      {/* Tabela */}
      <div className="overflow-y-auto flex-1">
        <table className="custom-table">
          <thead>
            <tr>
              <th className="w-10">Linha</th>
              <th>Cotação</th>
              <th>Motorista / Placa</th>
              <th>Valor</th>
              <th>Status</th>
              <th className="w-12 text-right">Det.</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center py-8 text-ink-dim italic text-xs">
                  {items.length === 0
                    ? 'Nenhum item ainda — aguardando upload.'
                    : 'Nenhum item para o filtro atual.'}
                </td>
              </tr>
            ) : (
              filtered.map((it) => {
                const isRowActive = activeItem?.nro_cotacao === it.nro_cotacao
                const isSelected = selectedItem?.nro_cotacao === it.nro_cotacao
                return (
                  <tr
                    key={it.id || it.row_index}
                    onClick={() => onSelect(it)}
                    className={`cursor-pointer ${isSelected ? 'row-selected' : ''}`}
                  >
                    <td className="font-mono text-[11px] text-ink-dim">{it.row_index}</td>
                    <td className="font-mono text-xs font-semibold text-accent">
                      {it.nro_cotacao}
                      {isRowActive && (
                        <span className="ml-1.5 w-1.5 h-1.5 rounded-full bg-ok pulse-dot inline-block align-middle" />
                      )}
                    </td>
                    <td>
                      <span className="text-xs block leading-tight">{it.nome || 'N/A'}</span>
                      <span className="font-mono text-[10px] text-ink-muted">{it.placa}</span>
                    </td>
                    <td className="font-mono text-[11px] text-ink-muted">
                      {it.frete_negociado || it.frete_a_pagar || '—'}
                    </td>
                    <td>
                      <span
                        className={`pill ${
                          it.status === 'Concluído'
                            ? 'pill-success'
                            : it.status === 'Erro'
                            ? 'pill-error'
                            : it.status === 'Em Processamento'
                            ? 'pill-primary'
                            : 'pill-muted'
                        }`}
                      >
                        {it.status}
                      </span>
                    </td>
                    <td className="text-right">
                      <span
                        title="Ver detalhes"
                        className="inline-flex p-1 rounded text-ink-dim hover:text-accent hover:bg-accent-soft cursor-pointer"
                      >
                        <EyeIcon />
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Drawer inferior de detalhes do item selecionado */}
      {selectedItem && (
        <div className="border-t border-edge bg-raised p-4 animate-fadeIn">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-accent">
                {selectedItem.nro_cotacao}
              </span>
              <span
                className={`pill ${
                  selectedItem.status === 'Concluído'
                    ? 'pill-success'
                    : selectedItem.status === 'Erro'
                    ? 'pill-error'
                    : 'pill-muted'
                }`}
              >
                {selectedItem.status}
              </span>
            </div>
            <button
              onClick={() => onSelect(null)}
              className="text-ink-dim hover:text-ink cursor-pointer p-1"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 text-[11px]">
            <Detail label="Linha / Cotação">
              <span className="font-mono">
                #{selectedItem.row_index} · {selectedItem.nro_cotacao}
              </span>
            </Detail>
            <Detail label="CTe emitido">
              {selectedItem.cte_number ? (
                <span className="font-mono font-bold text-ok">{selectedItem.cte_number}</span>
              ) : (
                <span className="text-ink-dim">—</span>
              )}
            </Detail>
            <Detail label="Motorista">
              {selectedItem.nome || 'N/A'} · <span className="font-mono">{selectedItem.placa}</span>
            </Detail>
            <Detail label="Duração">
              {selectedItem.duration_seconds != null
                ? `${selectedItem.duration_seconds.toFixed(1)}s`
                : '—'}
            </Detail>
            {selectedItem.error_message && (
              <div className="col-span-2 p-2.5 rounded-lg bg-bad/10 border border-bad/25">
                <p className="text-[10px] font-bold uppercase text-bad mb-1">Motivo do erro</p>
                <p className="text-[11px] text-ink">{selectedItem.error_message}</p>
              </div>
            )}
          </div>

          {/* Screenshot de evidência */}
          <ItemScreenshot jobId={selectedItem.job_id} cotacao={selectedItem.nro_cotacao} onOpenScreenshot={onOpenScreenshot} />
          <ItemArtifacts jobId={selectedItem.job_id} cotacao={selectedItem.nro_cotacao} />
        </div>
      )}
    </div>
  )
}

/* Busca screenshot do item na lista de artifacts */
function ItemScreenshot({ jobId, cotacao, onOpenScreenshot }) {
  const [shot, setShot] = useState(null)

  useEffect(() => {
    let alive = true
    setShot(null)
    if (!jobId || !cotacao) return
    api
      .getJobArtifacts(jobId)
      .then((data) => {
        if (!alive) return
        const match = (data?.artifacts || []).find(
          (a) => String(a.nro_cotacao) === String(cotacao) && a.artifact_type?.includes('SCREENSHOT')
        )
        if (match) {
          setShot(`${api.API_BASE}/api/v2/jobs/${jobId}/download/${match.id}`)
        }
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [jobId, cotacao])

  if (!shot) return null
  return (
    <button
      onClick={() => onOpenScreenshot(shot)}
      className="mt-3 flex items-center gap-1.5 text-[11px] text-accent hover:underline cursor-pointer"
    >
      <EyeIcon /> Ver screenshot de evidência
    </button>
  )
}

/* Artefatos não-screenshot do item (planilha linha, json etc.) com download */
function ItemArtifacts({ jobId, cotacao }) {
  const [arts, setArts] = useState([])

  useEffect(() => {
    let alive = true
    setArts([])
    if (!jobId || !cotacao) return
    api
      .getJobArtifacts(jobId)
      .then((data) => {
        if (!alive) return
        const others = (data?.artifacts || []).filter(
          (a) => String(a.nro_cotacao) === String(cotacao) && !a.artifact_type?.includes('SCREENSHOT')
        )
        setArts(others)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [jobId, cotacao])

  if (!arts.length) return null
  return (
    <div className="mt-2 space-y-1">
      {arts.map((a) => (
        <a
          key={a.id}
          href={`${api.API_BASE}/api/v2/jobs/${jobId}/download/${a.id}`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-[11px] text-accent hover:underline"
        >
          ⬇ <span className="font-mono uppercase">{a.artifact_type}</span>
          <span className="text-ink-muted truncate">{a.file_name}</span>
        </a>
      ))}
    </div>
  )
}

/* ---------- helpers & icons ---------- */

function Detail({ label, children }) {
  return (
    <div className="p-2 rounded bg-app border border-edge">
      <p className="text-[10px] uppercase text-ink-dim mb-0.5">{label}</p>
      {children}
    </div>
  )
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

function UploadIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-ink-dim">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent shrink-0">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}
