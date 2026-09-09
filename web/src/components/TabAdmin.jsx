import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'

export default function TabAdmin({ jobs = [], config, onSaveConfig, showToast }) {
  const [tab, setTab] = useState('visao')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-1 border-b border-edge pb-px">
        {[
          { id: 'visao', label: 'Visão Geral' },
          { id: 'trace', label: 'Trace & Audit' },
          { id: 'logs', label: 'Sessões de Log' },
          { id: 'seletores', label: 'Seletores DOM' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-xs font-semibold rounded-t-md border-b-2 transition-colors ${
              tab === t.id
                ? 'text-accent border-accent'
                : 'text-ink-muted border-transparent hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'visao' && <VisaoGeral jobs={jobs} />}
      {tab === 'trace' && <TraceAudit jobs={jobs} />}
      {tab === 'logs' && <SessoesLog showToast={showToast} />}
      {tab === 'seletores' && <SeletoresDom showToast={showToast} />}
    </div>
  )
}

/* ============ Visão Geral: KPIs + saúde ============ */
function VisaoGeral({ jobs }) {
  const stats = useMemo(() => {
    const completed = jobs.filter((j) => j.status === 'COMPLETED')
    const failed = jobs.filter((j) => j.status === 'FAILED')
    const cancelled = jobs.filter((j) => j.status === 'CANCELLED')
    const running = jobs.filter((j) => j.status === 'RUNNING' || j.status === 'PAUSED')

    const totalItems = jobs.reduce((s, j) => s + (j.total_items || 0), 0)
    const totalOk = jobs.reduce((s, j) => s + (j.success_count || 0), 0)
    const totalErr = jobs.reduce((s, j) => s + (j.error_count || 0), 0)
    const successRate = totalItems ? ((totalOk / totalItems) * 100).toFixed(1) : '—'

    const durations = jobs.filter((j) => j.duration_seconds > 0 && j.total_items > 0)
    const avgPerItem = durations.length
      ? durations.reduce((s, j) => s + j.duration_seconds / j.total_items, 0) / durations.length
      : null

    return { completed: completed.length, failed: failed.length, cancelled: cancelled.length, running: running.length, totalItems, totalOk, totalErr, successRate, avgPerItem }
  }, [jobs])

  return (
    <div className="space-y-5">
      {/* Cards de KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Lotes executados" value={stats.completed} tone="ok" sub={`${stats.failed} falha · ${stats.cancelled} cancel.`} />
        <Kpi label="Taxa de sucesso" value={`${stats.successRate}${stats.successRate !== '—' ? '%' : ''}`} tone={stats.successRate >= 90 ? 'ok' : stats.successRate >= 70 ? 'warn' : 'bad'} sub={`${stats.totalOk}/${stats.totalItems} itens`} />
        <Kpi label="Itens com falha" value={stats.totalErr} tone={stats.totalErr ? 'bad' : 'ok'} sub="acumulado" />
        <Kpi label="Tempo médio / item" value={stats.avgPerItem != null ? `${stats.avgPerItem.toFixed(1)}s` : '—'} tone="neutral" sub="por item, média global" />
      </div>

      {/* Falhas por fase (a partir dos jobs com error_summary) */}
      <FalhasPorFase jobs={jobs} />

      {/* Últimos lotes */}
      <div className="card-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-edge">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">Últimos lotes</h3>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: 360 }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Lote</th>
                <th>Status</th>
                <th>Itens</th>
                <th>OK / Falha</th>
                <th>Duração</th>
                <th>Operador</th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 20).map((j) => (
                <tr key={j.id}>
                  <td className="font-mono text-[11px] text-accent">{shortId(j.id)}</td>
                  <td>
                    <span className={`pill ${jobPill(j.status)}`}>{jobStatusLabel(j.status)}</span>
                  </td>
                  <td className="font-mono text-xs">{j.total_items ?? '—'}</td>
                  <td className="font-mono text-[11px]">
                    <span className="text-ok">{j.success_count ?? 0}</span>
                    <span className="text-ink-dim"> / </span>
                    <span className="text-bad">{j.error_count ?? 0}</span>
                  </td>
                  <td className="font-mono text-[11px] text-ink-muted">
                    {j.duration_seconds ? fmtDur(j.duration_seconds) : '—'}
                  </td>
                  <td className="font-mono text-[11px] text-ink-muted truncate max-w-[140px]">
                    {j.user_credentials_username || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

/* ============ Falhas por fase ============ */
function FalhasPorFase({ jobs }) {
  const byPhase = useMemo(() => {
    const counts = {}
    for (const j of jobs) {
      const s = j.error_summary
      if (!s) continue
      try {
        const parsed = typeof s === 'string' ? JSON.parse(s) : s
        for (const [phase, n] of Object.entries(parsed)) {
          counts[phase] = (counts[phase] || 0) + Number(n || 0)
        }
      } catch (e) {
        counts['outros'] = (counts['outros'] || 0) + 1
      }
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [jobs])

  if (byPhase.length === 0) return null

  const max = Math.max(...byPhase.map(([, n]) => n), 1)

  return (
    <div className="card-panel p-4">
      <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted mb-3">
        Falhas por fase
      </h3>
      <div className="space-y-2">
        {byPhase.map(([phase, n]) => (
          <div key={phase} className="flex items-center gap-3">
            <span className="font-mono text-[11px] text-ink w-10 shrink-0">{phase}</span>
            <div className="flex-1 h-2 bg-app rounded-full overflow-hidden">
              <div className="h-full bg-bad/70 rounded-full" style={{ width: `${(n / max) * 100}%` }} />
            </div>
            <span className="font-mono text-[11px] text-bad w-8 text-right">{n}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ============ Trace & Audit ============ */
function TraceAudit({ jobs }) {
  const byOperator = useMemo(() => {
    const map = {}
    for (const j of jobs) {
      const op = j.user_credentials_username || '(sem credencial)'
      if (!map[op]) map[op] = { lots: 0, items: 0, ok: 0, err: 0, lastAt: null }
      map[op].lots++
      map[op].items += j.total_items || 0
      map[op].ok += j.success_count || 0
      map[op].err += j.error_count || 0
      const t = j.created_at
      if (t && (!map[op].lastAt || t > map[op].lastAt)) map[op].lastAt = t
    }
    return Object.entries(map).sort((a, b) => b[1].lots - a[1].lots)
  }, [jobs])

  return (
    <div className="space-y-5">
      <div className="card-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-edge flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
            Trace por operador (credencial SSW)
          </h3>
          <span className="text-[10px] text-ink-dim font-mono">auditoria</span>
        </div>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Operador</th>
              <th>Lotes</th>
              <th>Itens</th>
              <th>OK / Falha</th>
              <th>Última execução</th>
            </tr>
          </thead>
          <tbody>
            {byOperator.length === 0 ? (
              <tr><td colSpan="5" className="text-center py-6 text-ink-dim italic text-xs">Nenhum dado de operador ainda.</td></tr>
            ) : (
              byOperator.map(([op, s]) => (
                <tr key={op}>
                  <td className="font-mono text-xs font-semibold">{op}</td>
                  <td className="font-mono text-[11px]">{s.lots}</td>
                  <td className="font-mono text-[11px]">{s.items}</td>
                  <td className="font-mono text-[11px]">
                    <span className="text-ok">{s.ok}</span>
                    <span className="text-ink-dim"> / </span>
                    <span className="text-bad">{s.err}</span>
                  </td>
                  <td className="font-mono text-[11px] text-ink-muted">{s.lastAt || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ============ Sessões de Log ============ */
function SessoesLog({ showToast }) {
  const [sessions, setSessions] = useState([])
  const [current, setCurrent] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listLogSessions()
      .then((d) => setSessions(d.sessions || d || []))
      .catch(() => showToast('Erro ao listar sessões de log', 'error'))
      .finally(() => setLoading(false))
  }, [])

  const openSession = async (id) => {
    try {
      const d = await api.getLogSession(id)
      setCurrent({ id, ...d })
    } catch (e) {
      showToast('Erro ao abrir sessão', 'error')
    }
  }

  return (
    <div className="space-y-4">
      <div className="card-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-edge flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
            Sessões de log do sistema
          </h3>
          <span className="font-mono text-[10px] text-ink-dim">{sessions.length} sessões</span>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: 300 }}>
          {loading ? (
            <p className="text-xs text-ink-dim p-4 italic">Carregando…</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-ink-dim p-4 italic">Nenhuma sessão de log encontrada.</p>
          ) : (
            <table className="custom-table">
              <thead>
                <tr><th>Sessão</th><th>Ações</th></tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id || s.id}>
                    <td className="font-mono text-[11px]">{s.session_id || s.id || s.name}</td>
                    <td>
                      <button onClick={() => openSession(s.session_id || s.id)} className="text-[11px] text-accent hover:underline cursor-pointer">
                        Abrir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {current && (
        <div className="terminal p-4 overflow-y-auto animate-fadeIn" style={{ maxHeight: 380 }}>
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[10px] text-ink-dim">{current.id}</span>
            <button onClick={() => setCurrent(null)} className="text-ink-dim hover:text-ink cursor-pointer text-xs">✕</button>
          </div>
          <pre className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-[var(--terminal-text)]">
            {typeof current.content === 'string' ? current.content : JSON.stringify(current, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

/* ============ Seletores DOM ============ */
function SeletoresDom({ showToast }) {
  const [selectors, setSelectors] = useState(null)
  const [raw, setRaw] = useState('')
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    api.getSelectorsConfig()
      .then((d) => {
        setSelectors(d)
        setRaw(JSON.stringify(d, null, 2))
      })
      .catch(() => showToast('Erro ao carregar seletores', 'error'))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const parsed = JSON.parse(raw)
      // PUT /config/selectors não existe no backend; usa /config com a chave selectors
      const cfg = await api.getConfig()
      await api.saveConfig({ ...cfg, selectors: parsed })
      setSelectors(parsed)
      setEditing(false)
      showToast('Seletores salvos com sucesso', 'success')
    } catch (e) {
      showToast(`JSON inválido ou erro ao salvar: ${e.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  if (!selectors) return <p className="text-xs text-ink-dim italic">Carregando seletores…</p>

  return (
    <div className="card-panel overflow-hidden">
      <div className="px-4 py-3 border-b border-edge flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          Catálogo Centralizado de Seletores DOM
        </h3>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button onClick={handleSave} disabled={saving} className="btn btn-primary text-xs">
                {saving ? 'Salvando…' : 'Salvar'}
              </button>
              <button onClick={() => { setEditing(false); setRaw(JSON.stringify(selectors, null, 2)) }} className="btn btn-secondary text-xs">
                Cancelar
              </button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="btn btn-secondary text-xs">
              Editar
            </button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="p-4">
          <textarea
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            spellCheck={false}
            className="w-full terminal p-4 font-mono text-[11px] leading-relaxed rounded-lg"
            style={{ minHeight: 420 }}
          />
        </div>
      ) : (
        <div className="overflow-y-auto p-4" style={{ maxHeight: 520 }}>
          <SelectorsTree node={selectors} path="" />
        </div>
      )}
    </div>
  )
}

function SelectorsTree({ node, path }) {
  if (node === null || typeof node !== 'object') {
    return (
      <span className="font-mono text-[11px] text-ok">{JSON.stringify(node)}</span>
    )
  }
  const entries = Object.entries(node)
  return (
    <div className={path ? 'ml-3 border-l border-edge pl-3' : ''}>
      {entries.map(([k, v]) => {
        const isLeaf = v === null || typeof v !== 'object'
        return (
          <div key={k} className="py-0.5">
            <span className="font-mono text-[11px] text-accent">{k}</span>
            {isLeaf ? (
              <>
                <span className="font-mono text-[11px] text-ink-dim">: </span>
                <SelectorsTree node={v} path={path} />
              </>
            ) : (
              <SelectorsTree node={v} path={path ? `${path}.${k}` : k} />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ============ helpers ============ */
function Kpi({ label, value, tone = 'neutral', sub }) {
  const toneClass = {
    ok: 'text-ok',
    warn: 'text-warn',
    bad: 'text-bad',
    neutral: 'text-ink',
    accent: 'text-accent',
  }[tone]
  return (
    <div className="card-panel p-4">
      <p className="text-[10px] font-bold uppercase tracking-wider text-ink-dim">{label}</p>
      <p className={`font-mono text-2xl font-bold mt-1 ${toneClass}`}>{value}</p>
      {sub && <p className="text-[10px] text-ink-dim mt-1">{sub}</p>}
    </div>
  )
}

function jobStatusLabel(status) {
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

function jobPill(status) {
  return {
    COMPLETED: 'pill-success',
    FAILED: 'pill-error',
    CANCELLED: 'pill-warning',
    PENDING: 'pill-muted',
    RUNNING: 'pill-primary',
    PAUSED: 'pill-warning',
  }[status] || 'pill-muted'
}

function shortId(id = '') {
  const m = id.match(/job_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}_(\w+)/)
  if (m) return `${m[3]}/${m[2]} ${m[4]}:${m[5]} · ${m[6]}`
  return id
}

function fmtDur(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(0)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m${s.toString().padStart(2, '0')}s`
}
