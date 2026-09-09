import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'

export default function TabHistorico({
  jobs = [],
  onSelectJobForDetail,
  selectedJobDetail,
  onCloseDrawer,
  onOpenScreenshot,
}) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('TODOS')

  const filtered = useMemo(() => {
    return jobs.filter((j) => {
      const q = search.toLowerCase()
      const matchSearch =
        !q ||
        (j.filename || '').toLowerCase().includes(q) ||
        (j.id || '').toLowerCase().includes(q) ||
        (j.user_credentials_username || '').toLowerCase().includes(q)
      const matchStatus = statusFilter === 'TODOS' || j.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [jobs, search, statusFilter])

  useEffect(() => {
    if (selectedJobDetail) {
      // refresh ao abrir
    }
  }, [selectedJobDetail])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-bold text-ink">
          Histórico de Lotes
          <span className="text-ink-dim font-normal font-mono text-xs ml-2">
            {filtered.length} de {jobs.length}
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Buscar por arquivo, lote, operador…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field w-64"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-field w-36 font-mono text-xs"
          >
            <option value="TODOS">TODOS</option>
            <option value="COMPLETED">Concluídos</option>
            <option value="FAILED">Falhos</option>
            <option value="CANCELLED">Cancelados</option>
            <option value="RUNNING">Executando</option>
          </select>
        </div>
      </div>

      <div className="card-panel overflow-hidden">
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Lote</th>
                <th>Arquivo</th>
                <th>Status</th>
                <th>Progresso</th>
                <th>Itens</th>
                <th>Duração</th>
                <th>Criado em</th>
                <th className="text-right">Rastreio</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-10 text-ink-dim italic text-xs">
                    Nenhum lote encontrado.
                  </td>
                </tr>
              ) : (
                filtered.map((j) => {
                  const pct = j.total_items
                    ? Math.round(((j.success_count || 0) / j.total_items) * 100)
                    : 0
                  return (
                    <tr key={j.id} className="cursor-pointer" onClick={() => onSelectJobForDetail(j.id)}>
                      <td className="font-mono text-[11px] text-accent">{shortId(j.id)}</td>
                      <td className="text-xs max-w-[220px] truncate" title={j.filename}>
                        {j.filename || '—'}
                      </td>
                      <td>
                        <span className={`pill ${pillFor(j.status)}`}>{labelFor(j.status)}</span>
                      </td>
                      <td style={{ minWidth: 90 }}>
                        <div className="progress-track" style={{ height: 4 }}>
                          <div
                            className="progress-fill"
                            style={{
                              width: `${pct}%`,
                              background: j.status === 'FAILED' ? 'var(--color-bad)' : undefined,
                            }}
                          />
                        </div>
                      </td>
                      <td className="font-mono text-[11px]">
                        <span className="text-ok">{j.success_count ?? 0}</span>
                        <span className="text-ink-dim">/</span>
                        <span className="text-ink-muted">{j.total_items ?? 0}</span>
                        {(j.error_count || 0) > 0 && (
                          <span className="text-bad ml-1">({j.error_count} err)</span>
                        )}
                      </td>
                      <td className="font-mono text-[11px] text-ink-muted">
                        {j.duration_seconds ? fmtDur(j.duration_seconds) : '—'}
                      </td>
                      <td className="font-mono text-[11px] text-ink-muted">{fmtDate(j.created_at)}</td>
                      <td className="text-right whitespace-nowrap">
                        <span
                          title="Ver rastreio"
                          onClick={(e) => {
                            e.stopPropagation()
                            onSelectJobForDetail(j.id)
                          }}
                          className="inline-flex p-1 rounded text-ink-dim hover:text-accent hover:bg-accent-soft cursor-pointer"
                        >
                          <EyeIcon />
                        </span>
                        <JobExcelDownload jobId={j.id} />
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer lateral: rastreio completo do lote */}
      {selectedJobDetail && (
        <JobDetailDrawer
          detail={selectedJobDetail}
          onClose={onCloseDrawer}
          onOpenScreenshot={onOpenScreenshot}
        />
      )}
    </div>
  )
}

/* Ícone de download da planilha final (EXCEL_RESULT) por lote */
function JobExcelDownload({ jobId }) {
  const [excel, setExcel] = useState(null)

  useEffect(() => {
    let alive = true
    setExcel(null)
    if (!jobId) return
    api
      .getJobArtifacts(jobId)
      .then((data) => {
        if (!alive) return
        const match = (data?.artifacts || []).find((a) => a.artifact_type === 'EXCEL_RESULT')
        if (match) setExcel(match)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [jobId])

  if (!excel) return null
  return (
    <a
      href={`${api.API_BASE}/api/v2/jobs/${jobId}/download/${excel.id}`}
      title={`Baixar planilha final: ${excel.file_name}`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex p-1 rounded text-ink-dim hover:text-ok hover:bg-ok/10 cursor-pointer ml-1"
    >
      <DownloadIcon />
    </a>
  )
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

/* ============ Drawer de rastreio do lote ============ */
function JobDetailDrawer({ detail, onClose, onOpenScreenshot }) {
  const job = detail.job || {}
  const items = detail.items || []
  const artifacts = detail.artifacts || []

  const statusCounts = useMemo(() => {
    const c = { Concluído: 0, Erro: 0, Pendente: 0, outro: 0 }
    for (const it of items) {
      if (it.status in c) c[it.status]++
      else c.outro++
    }
    return c
  }, [items])

  const [selectedItem, setSelectedItem] = useState(null)

  return (
    <div className="fixed inset-0 z-40 flex justify-end animate-fadeIn" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-3xl h-full bg-surface border-l border-edge overflow-y-auto animate-slideLeft"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface border-b border-edge px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`pill ${pillFor(job.status)}`}>{labelFor(job.status)}</span>
              <span className="font-mono text-[11px] text-ink-dim">{job.id}</span>
            </div>
            <p className="text-sm font-semibold text-ink truncate">{job.filename || '—'}</p>
            <p className="font-mono text-[11px] text-ink-muted mt-0.5">
              {job.created_at} · {job.duration_seconds ? fmtDur(job.duration_seconds) : 'em aberto'} ·{' '}
              operador: <span className="text-ink">{job.user_credentials_username || '—'}</span>
            </p>
          </div>
          <button onClick={onClose} className="text-ink-dim hover:text-ink text-sm cursor-pointer shrink-0">
            ✕ Fechar
          </button>
        </div>

        {/* Resumo */}
        <div className="grid grid-cols-3 gap-3 px-5 py-4">
          <MiniStat label="Concluídos" value={statusCounts.Concluído} tone="text-ok" />
          <MiniStat label="Erros" value={statusCounts.Erro} tone="text-bad" />
          <MiniStat label="Pendentes" value={statusCounts.Pendente} tone="text-ink-muted" />
        </div>

        {/* Tabela de itens */}
        <div className="px-5 pb-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted mb-2">
            Itens ({items.length})
          </h4>
          <div className="card-panel overflow-hidden">
            <div className="overflow-y-auto" style={{ maxHeight: 420 }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th className="w-10">Linha</th>
                    <th>Cotação</th>
                    <th>Motorista / Placa</th>
                    <th>CTe</th>
                    <th>Status</th>
                    <th className="w-10 text-right">Det.</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="text-center py-8 text-ink-dim italic text-xs">
                        Nenhum item registrado.
                      </td>
                    </tr>
                  ) : (
                    items.map((it) => (
                      <tr key={it.id || it.row_index} className="cursor-pointer" onClick={() => setSelectedItem(it)}>
                        <td className="font-mono text-[11px] text-ink-dim">{it.row_index}</td>
                        <td className="font-mono text-xs font-semibold text-accent">{it.nro_cotacao}</td>
                        <td>
                          <span className="text-xs block leading-tight">{it.nome || 'N/A'}</span>
                          <span className="font-mono text-[10px] text-ink-muted">{it.placa}</span>
                        </td>
                        <td className="font-mono text-[11px]">
                          {it.cte_number ? (
                            <span className="font-bold text-ok">{it.cte_number}</span>
                          ) : (
                            <span className="text-ink-dim">—</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`pill ${
                              it.status === 'Concluído'
                                ? 'pill-success'
                                : it.status === 'Erro'
                                ? 'pill-error'
                                : 'pill-muted'
                            }`}
                          >
                            {it.status}
                          </span>
                        </td>
                        <td className="text-right">
                          <span className="inline-flex p-1 rounded text-ink-dim">
                            <EyeIcon />
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Detalhe do item + screenshot */}
        {selectedItem && (
          <div className="mx-5 mb-5 p-4 rounded-lg bg-raised border border-edge animate-fadeIn">
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
              <button onClick={() => setSelectedItem(null)} className="text-ink-dim hover:text-ink cursor-pointer">
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
              <Detail label="Remetente">
                {selectedItem.remetente || '—'}
              </Detail>
              <Detail label="Duração">
                {selectedItem.duration_seconds != null
                  ? `${selectedItem.duration_seconds.toFixed(1)}s`
                  : '—'}
              </Detail>
              <Detail label="NF extraída">
                <span className="font-mono">{selectedItem.extracted_nf || '—'}</span>
              </Detail>
              <Detail label="Nº Pedido extraído">
                <span className="font-mono">{selectedItem.extracted_nro_pedido || '—'}</span>
              </Detail>
              {selectedItem.error_message && (
                <div className="col-span-2 p-2.5 rounded-lg bg-bad/10 border border-bad/25">
                  <p className="text-[10px] font-bold uppercase text-bad mb-1">Motivo do erro</p>
                  <p className="text-[11px] text-ink">{selectedItem.error_message}</p>
                </div>
              )}
            </div>

            <ItemScreenshot jobId={job.id} cotacao={selectedItem.nro_cotacao} onOpenScreenshot={onOpenScreenshot} />
          </div>
        )}

        {/* Artifacts do lote */}
        {artifacts.length > 0 && (
          <div className="mx-5 mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted mb-2">
              Artifacts ({artifacts.length})
            </h4>
            <div className="space-y-1.5">
              {artifacts.map((a) => (
                <a
                  key={a.id}
                  href={`${api.API_BASE}/api/v2/jobs/${job.id}/download/${a.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 p-2 rounded bg-raised border border-edge hover:border-accent/50 transition-colors cursor-pointer"
                >
                  <span className="font-mono text-[10px] text-ink-dim uppercase">{a.artifact_type}</span>
                  <span className="text-[11px] text-ink truncate flex-1">{a.file_name}</span>
                  {a.nro_cotacao && (
                    <span className="font-mono text-[10px] text-accent">{a.nro_cotacao}</span>
                  )}
                  <span className="font-mono text-[10px] text-ink-dim">{fmtBytes(a.file_size_bytes)}</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

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
        if (match) setShot(`${api.API_BASE}/api/v2/jobs/${jobId}/download/${match.id}`)
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

/* ============ helpers ============ */
function MiniStat({ label, value, tone = 'text-ink' }) {
  return (
    <div className="p-3 rounded-lg bg-raised border border-edge">
      <p className="text-[10px] uppercase text-ink-dim">{label}</p>
      <p className={`font-mono text-xl font-bold mt-0.5 ${tone}`}>{value}</p>
    </div>
  )
}

function Detail({ label, children }) {
  return (
    <div className="p-2 rounded bg-app border border-edge">
      <p className="text-[10px] uppercase text-ink-dim mb-0.5">{label}</p>
      {children}
    </div>
  )
}

function pillFor(status) {
  return {
    COMPLETED: 'pill-success',
    FAILED: 'pill-error',
    CANCELLED: 'pill-warning',
    PENDING: 'pill-muted',
    RUNNING: 'pill-primary',
    PAUSED: 'pill-warning',
  }[status] || 'pill-muted'
}

function labelFor(status) {
  const map = {
    COMPLETED: 'Concluído',
    FAILED: 'Falhou',
    CANCELLED: 'Cancelado',
    PENDING: 'Aguardando',
    RUNNING: 'Executando',
    PAUSED: 'Pausado',
  }
  return map[status] || status || '—'
}

function shortId(id = '') {
  const m = id.match(/job_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}_(\w+)/)
  if (m) return `${m[3]}/${m[2]} ${m[4]}:${m[5]} · ${m[6]}`
  return id
}

function fmtDate(iso) {
  if (!iso) return '—'
  return String(iso).replace('T', ' ').slice(0, 16)
}

function fmtDur(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(0)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m${s.toString().padStart(2, '0')}s`
}

function fmtBytes(b) {
  if (b == null) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

function EyeIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}
