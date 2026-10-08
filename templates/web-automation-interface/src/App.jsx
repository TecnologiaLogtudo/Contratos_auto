import React, { useEffect, useMemo, useState } from 'react'
import { api } from './services/api.js'
import { connectJobStream } from './services/realtime.js'
import { templateConfig } from './template.config.js'

const statusLabels = {
  PENDING: 'Aguardando', RUNNING: 'Executando', PAUSED: 'Pausado',
  COMPLETED: 'Concluído', FAILED: 'Falhou', CANCELLED: 'Cancelado',
}

export default function App() {
  const [tab, setTab] = useState('execution')
  const [connected, setConnected] = useState(false)
  const [jobs, setJobs] = useState([])
  const [currentJob, setCurrentJob] = useState(null)
  const [items, setItems] = useState([])
  const [logs, setLogs] = useState([])
  const [config, setConfig] = useState({})
  const [toast, setToast] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('automation_theme') || 'dark')

  useEffect(() => {
    document.documentElement.className = theme
    localStorage.setItem('automation_theme', theme)
  }, [theme])

  useEffect(() => {
    Promise.allSettled([api.health(), api.listJobs(), api.getConfig()]).then(([health, list, settings]) => {
      setConnected(health.status === 'fulfilled')
      if (list.status === 'fulfilled') setJobs(list.value.jobs || [])
      if (settings.status === 'fulfilled') setConfig(settings.value || {})
    })
  }, [])

  useEffect(() => connectJobStream(currentJob?.id, {
    onConnection: setConnected,
    onEvent: (event) => {
      if (event.type === 'log') setLogs((old) => [...old, event.data || event])
      if (event.type === 'progress' || event.type === 'job_update') {
        setCurrentJob((old) => ({ ...old, ...(event.data || event) }))
      }
    },
  }), [currentJob?.id])

  function notify(message, tone = 'ok') {
    setToast({ message, tone })
    window.setTimeout(() => setToast(null), 3500)
  }

  async function refreshJobs() {
    const response = await api.listJobs()
    setJobs(response.jobs || [])
  }

  async function openJob(jobId) {
    const detail = await api.getJob(jobId)
    setCurrentJob(detail.job)
    setItems(detail.items || [])
    setLogs(detail.logs || [])
    setTab('execution')
  }

  const status = currentJob?.status || 'PENDING'
  const percent = currentJob?.percent ?? (currentJob?.total_items ? (currentJob.success_count || 0) / currentJob.total_items : 0)

  return (
    <div className="app-shell">
      <Sidebar tab={tab} setTab={setTab} connected={connected} currentJob={currentJob} percent={percent} theme={theme} setTheme={setTheme} />
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">CENTRAL OPERACIONAL</p>
            <h1>{templateConfig.navigation.find((item) => item.id === tab)?.label}</h1>
          </div>
          <span className={`status-pill ${connected ? 'success' : 'warning'}`}>{connected ? 'Sistema pronto' : 'Reconectando'}</span>
        </header>

        {tab === 'execution' && (
          <ExecutionPanel
            currentJob={currentJob} items={items} logs={logs} config={config}
            setConfig={setConfig} setCurrentJob={setCurrentJob} setItems={setItems}
            setLogs={setLogs} refreshJobs={refreshJobs} notify={notify}
          />
        )}
        {tab === 'history' && <HistoryPanel jobs={jobs} refresh={refreshJobs} openJob={openJob} />}
        {tab === 'admin' && <AdminPanel jobs={jobs} config={config} setConfig={setConfig} notify={notify} />}
      </main>
      {toast && <div className={`toast ${toast.tone}`}>{toast.message}</div>}
    </div>
  )
}

function Sidebar({ tab, setTab, connected, currentJob, percent, theme, setTheme }) {
  const pct = Math.round(Math.min(1, Math.max(0, percent || 0)) * 100)
  return (
    <aside className="sidebar">
      <div className="brand">
        {templateConfig.brand.logoUrl ? <img src={templateConfig.brand.logoUrl} alt="" /> : <div className="brand-mark">A</div>}
        <div><strong>{templateConfig.brand.organization}</strong><span>{templateConfig.brand.product} · v{templateConfig.brand.version}</span></div>
      </div>
      <nav>{templateConfig.navigation.map((item) => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}>{item.label}</button>)}</nav>
      <section className="active-job">
        <p className="eyebrow">LOTE ATIVO</p>
        {currentJob ? <>
          <strong className="mono">{currentJob.id}</strong>
          <div className="metric-line"><span>{currentJob.success_count || 0}/{currentJob.total_items || 0}</span><b>{pct}%</b></div>
          <Progress value={pct} />
          <span className={`status-pill ${toneFor(currentJob.status)}`}>{statusLabels[currentJob.status] || currentJob.status}</span>
        </> : <span className="muted">Nenhum lote selecionado</span>}
      </section>
      <div className="sidebar-footer">
        <span className="connection"><i className={connected ? 'online' : ''} />{connected ? 'API conectada' : 'API indisponível'}</span>
        <button className="ghost" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? 'Tema escuro' : 'Tema claro'}</button>
      </div>
    </aside>
  )
}

function ExecutionPanel({ currentJob, items, logs, config, setConfig, setCurrentJob, setItems, setLogs, refreshJobs, notify }) {
  const [validation, setValidation] = useState(null)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState(null)
  const running = currentJob?.status === 'RUNNING'
  const paused = currentJob?.status === 'PAUSED'

  async function upload(file) {
    if (!file) return
    setBusy(true)
    try {
      const report = await api.uploadAndValidate(file)
      setValidation(report)
      const detail = await api.getJob(report.job_id)
      setCurrentJob(detail.job)
      setItems(detail.items || report.preview || [])
      setLogs([])
      await refreshJobs()
      notify(`${report.valid_rows_count} itens válidos para processamento`)
    } catch (error) { notify(error.message, 'bad') } finally { setBusy(false) }
  }

  async function start() {
    if (!currentJob?.id) return notify('Selecione e valide um arquivo primeiro', 'bad')
    setBusy(true)
    try {
      await api.startJob(currentJob.id, {
        usuario: config.username || '', senha: config.password || '',
        headless: config.headless ?? true, throttle_seconds: Number(config.throttleSeconds ?? 2.5),
      })
      setCurrentJob((old) => ({ ...old, status: 'RUNNING' }))
      setLogs((old) => [...old, { timestamp: new Date().toLocaleTimeString(), level: 'INFO', phase: 'GERAL', message: 'Execução iniciada.' }])
      notify('Automação iniciada')
    } catch (error) { notify(error.message, 'bad') } finally { setBusy(false) }
  }

  async function action(name) {
    try {
      await api.action(currentJob.id, name)
      const status = name === 'pause' ? 'PAUSED' : name === 'resume' ? 'RUNNING' : 'CANCELLED'
      setCurrentJob((old) => ({ ...old, status }))
      notify(statusLabels[status])
    } catch (error) { notify(error.message, 'bad') }
  }

  return (
    <div className="stack">
      {api.mockMode && <div className="demo-banner">Modo de demonstração ativo — a interface funciona sem backend.</div>}
      <section className="grid two">
        <div className="card upload-card">
          <div><p className="eyebrow">1 · PREPARAR</p><h2>{templateConfig.upload.title}</h2><p className="muted">{templateConfig.upload.help}</p></div>
          <label className="dropzone">
            <span>Solte o arquivo aqui ou clique para selecionar</span>
            <small>{templateConfig.upload.accept}</small>
            <input type="file" accept={templateConfig.upload.accept} onChange={(event) => upload(event.target.files?.[0])} disabled={busy || running} />
          </label>
          {validation && <div className="validation"><b>{validation.filename}</b><span>{validation.valid_rows_count} válidos · {validation.invalid_rows_count} inválidos</span></div>}
        </div>
        <div className="card">
          <p className="eyebrow">2 · EXECUTAR</p><h2>Controle da automação</h2>
          <div className="form-grid">
            {templateConfig.credentials.map((field) => <Field key={field.key} field={field} value={config[field.key] ?? ''} onChange={(value) => setConfig({ ...config, [field.key]: value })} />)}
          </div>
          <div className="actions">
            <button className="primary" onClick={start} disabled={!currentJob || running || busy}>Iniciar automação</button>
            <button onClick={() => action(paused ? 'resume' : 'pause')} disabled={!running && !paused}>{paused ? 'Continuar' : 'Pausar'}</button>
            <button className="danger" onClick={() => action('cancel')} disabled={!running && !paused}>Cancelar</button>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-heading"><div><p className="eyebrow">ACOMPANHAMENTO</p><h2>Fases do processamento</h2></div><span className={`status-pill ${toneFor(currentJob?.status)}`}>{statusLabels[currentJob?.status] || 'Aguardando'}</span></div>
        <Stepper currentPhase={currentJob?.current_phase || 'F1'} />
      </section>

      <section className="grid work-grid">
        <div className="card table-card">
          <div className="section-heading"><div><p className="eyebrow">ITENS</p><h2>Lote em processamento</h2></div><span className="muted">{items.length} registros</span></div>
          <div className="table-wrap"><table><thead><tr><th>Referência</th><th>Status</th><th>Mensagem</th></tr></thead><tbody>
            {items.length ? items.map((item, index) => <tr key={item.id || index} onClick={() => setSelected(item)} className={selected === item ? 'selected' : ''}><td className="mono">{item.reference || item.nro_cotacao || item.id}</td><td><span className={`status-pill ${toneFor(item.status)}`}>{statusLabels[item.status] || item.status || 'Aguardando'}</span></td><td>{item.message || item.error_message || '—'}</td></tr>) : <tr><td colSpan="3" className="empty">Carregue um arquivo para visualizar os itens.</td></tr>}
          </tbody></table></div>
        </div>
        <Terminal logs={logs} />
      </section>
    </div>
  )
}

function HistoryPanel({ jobs, refresh, openJob }) {
  const [query, setQuery] = useState('')
  useEffect(() => { refresh().catch(() => {}) }, [])
  const filtered = useMemo(() => jobs.filter((job) => `${job.id} ${job.filename}`.toLowerCase().includes(query.toLowerCase())), [jobs, query])
  return <section className="card"><div className="section-heading"><div><p className="eyebrow">RASTREABILIDADE</p><h2>Histórico de execuções</h2></div><input className="input compact" placeholder="Buscar lote ou arquivo" value={query} onChange={(event) => setQuery(event.target.value)} /></div><div className="table-wrap"><table><thead><tr><th>Lote</th><th>Arquivo</th><th>Status</th><th>Sucesso</th><th>Falhas</th><th>Início</th></tr></thead><tbody>{filtered.length ? filtered.map((job) => <tr key={job.id} onClick={() => openJob(job.id)}><td className="mono">{job.id}</td><td>{job.filename}</td><td><span className={`status-pill ${toneFor(job.status)}`}>{statusLabels[job.status] || job.status}</span></td><td>{job.success_count || 0}</td><td>{(job.error_count || 0) + (job.invalid_count || 0)}</td><td>{formatDate(job.created_at)}</td></tr>) : <tr><td colSpan="6" className="empty">Nenhuma execução registrada.</td></tr>}</tbody></table></div></section>
}

function AdminPanel({ jobs, config, setConfig, notify }) {
  const completed = jobs.filter((job) => job.status === 'COMPLETED').length
  const failed = jobs.filter((job) => job.status === 'FAILED').length
  async function save() {
    try { const saved = await api.saveConfig(config); setConfig(saved); notify('Configurações salvas') } catch (error) { notify(error.message, 'bad') }
  }
  return <div className="stack"><section className="stats"><Stat label="Execuções" value={jobs.length} /><Stat label="Concluídas" value={completed} /><Stat label="Com falha" value={failed} /><Stat label="Disponibilidade" value="Online" /></section><section className="card"><p className="eyebrow">CONFIGURAÇÃO</p><h2>Parâmetros operacionais</h2><div className="form-grid settings">{templateConfig.operationalSettings.map((field) => <Field key={field.key} field={field} value={config[field.key] ?? field.defaultValue} onChange={(value) => setConfig({ ...config, [field.key]: value })} />)}</div><button className="primary" onClick={save}>Salvar configurações</button></section><section className="card"><p className="eyebrow">CONTRATO DE INTEGRAÇÃO</p><h2>Funcionalidades periféricas previstas</h2><ul className="feature-list"><li>Validação de arquivo antes da execução</li><li>Persistência de jobs, itens e logs estruturados</li><li>WebSocket com reconexão para progresso em tempo real</li><li>Pausa, retomada e cancelamento controlados</li><li>Artefatos por lote: relatórios, screenshots e traces</li><li>Healthcheck, subcaminho de publicação e proxy local</li></ul></section></div>
}

function Field({ field, value, onChange }) {
  if (field.type === 'checkbox') return <label className="check"><input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} /><span>{field.label}</span></label>
  return <label><span>{field.label}</span><input className="input" type={field.type} value={value} min={field.min} required={field.required} onChange={(event) => onChange(field.type === 'number' ? Number(event.target.value) : event.target.value)} /></label>
}

function Stepper({ currentPhase }) {
  const index = Math.max(0, templateConfig.phases.findIndex((phase) => phase.id === currentPhase))
  return <div className="stepper">{templateConfig.phases.map((phase, position) => <div className={`step ${position < index ? 'done' : position === index ? 'current' : ''}`} key={phase.id}><span>{position < index ? '✓' : position + 1}</span><div><b>{phase.title}</b><small>{phase.subtitle}</small></div></div>)}</div>
}

function Terminal({ logs }) {
  const [level, setLevel] = useState('TODOS')
  const visible = logs.filter((log) => level === 'TODOS' || (log.level || '').toUpperCase() === level)
  return <div className="terminal"><div className="terminal-head"><div><p className="eyebrow">LOG AO VIVO</p><h2>Atividade</h2></div><select value={level} onChange={(event) => setLevel(event.target.value)}><option>TODOS</option><option>INFO</option><option>WARNING</option><option>ERROR</option></select></div><div className="terminal-body">{visible.length ? visible.map((log, index) => <p key={index}><time>{log.timestamp || '--:--:--'}</time><b className={(log.level || 'INFO').toLowerCase()}>{log.level || 'INFO'}</b><span>[{log.phase || 'GERAL'}] {log.message}</span></p>) : <p className="terminal-empty">Aguardando eventos da automação…</p>}</div></div>
}

function Progress({ value }) { return <div className="progress"><i style={{ width: `${value}%` }} /></div> }
function Stat({ label, value }) { return <div className="card stat"><span>{label}</span><strong>{value}</strong></div> }
function toneFor(status) { return ({ COMPLETED: 'success', RUNNING: 'success', PAUSED: 'warning', FAILED: 'bad', CANCELLED: 'bad' }[status] || 'neutral') }
function formatDate(value) { return value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—' }
