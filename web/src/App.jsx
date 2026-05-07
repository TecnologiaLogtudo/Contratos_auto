import { useEffect, useMemo, useRef, useState } from 'react'

const LEVELS = ['TODOS', 'INFO', 'DEBUG', 'AVISO', 'ERRO', 'SUCESSO', 'FASE']
const MENU_ITEMS = ['Processamento', 'Resultados', 'Manual', 'Logs']

const initialConfig = {
  login: '',
  senha: '',
  atraso_fases: 1,
  atraso_etapas: 0.3,
  dados_km: '10',
  aceitar_frete_minimo_antt: true,
}

export default function App() {
  const rawBasePath = (() => {
    if (typeof window !== 'undefined' && window.LOGTUDO_BASE_PATH) return String(window.LOGTUDO_BASE_PATH)
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.BASE_URL) return String(import.meta.env.BASE_URL)
    return ''
  })()
  const normalizedRawBasePath = rawBasePath.trim()
  const basePath = normalizedRawBasePath === '/' || normalizedRawBasePath.includes('__LOGTUDO_BASE_PATH__')
    ? ''
    : normalizedRawBasePath.replace(/\/+/g, '/').replace(/\/$/, '')
  const envApiBase = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL ? String(import.meta.env.VITE_API_BASE_URL) : '')
    .trim()
    .replace(/\/+$/, '')
  const API_BASE = envApiBase || basePath
  const manualRoute = `${basePath}/manual`
  const isManualPage = typeof window !== 'undefined' && window.location.pathname.replace(/\/+$/, '') === manualRoute
  const [config, setConfig] = useState(initialConfig)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [job, setJob] = useState(null)
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('TODOS')
  const [autoScroll, setAutoScroll] = useState(true)
  const [loading, setLoading] = useState(false)
  const [activeMenu, setActiveMenu] = useState('Processamento')
  const [showPassword, setShowPassword] = useState(false)
  const [history, setHistory] = useState([])
  const [selectedResults, setSelectedResults] = useState([])
  const [deletePassword, setDeletePassword] = useState('')
  const [toast, setToast] = useState(null)
  const [configErrors, setConfigErrors] = useState({})
  const [busyAction, setBusyAction] = useState('')
  const [logSessions, setLogSessions] = useState([])
  const [selectedLogSessionId, setSelectedLogSessionId] = useState('')
  const [logSessionDetail, setLogSessionDetail] = useState(null)
  const [logsTab, setLogsTab] = useState('acoes')
  const [clearLogsPassword, setClearLogsPassword] = useState('')
  const logsRef = useRef(null)
  const fileInputRef = useRef(null)
  const configCardRef = useRef(null)
  const loginInputRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/config`).then((r) => r.json()).then(setConfig).catch(() => {})
    loadHistory()
    loadLogSessions()
  }, [])

  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const r = await fetch(`${API_BASE}/api/jobs/${jobId}`)
      if (!r.ok) return
      const data = await r.json()
      setJob(data.status)
      if (data?.status?.log_session_id) setSelectedLogSessionId(data.status.log_session_id)
      if (['completed', 'error', 'stopped'].includes(data.status.state)) {
        loadHistory()
        loadLogSessions()
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/logs`)
    es.onmessage = (event) => setLogs((prev) => [...prev, JSON.parse(event.data)])
    es.onerror = () => es.close()
    return () => es.close()
  }, [jobId])

  useEffect(() => {
    if (autoScroll && logsRef.current) logsRef.current.scrollTop = logsRef.current.scrollHeight
  }, [logs, autoScroll])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4500)
    return () => clearTimeout(timer)
  }, [toast])

  const filteredLogs = useMemo(() => (filter === 'TODOS' ? logs : logs.filter((l) => l.level === filter)), [logs, filter])
  const progress = job?.percent || 0

  const metrics = useMemo(() => {
    const sucessos = history.reduce((acc, h) => acc + (h.sucessos || 0), 0)
    const erros = history.reduce((acc, h) => acc + (h.erros || 0), 0)
    const pendentes = history.reduce((acc, h) => acc + Math.max((h.total || 0) - (h.processados || 0), 0), 0)
    const total = sucessos + erros
    const taxa = total ? Math.round((sucessos / total) * 100) : 0
    return { sucessos, erros, pendentes, taxa }
  }, [history])

  function withBasePath(path) {
    const normalized = path.startsWith('/') ? path : `/${path}`
    return `${basePath}${normalized}`.replace(/\/+/g, '/')
  }

  async function loadHistory() {
    const r = await fetch(`${API_BASE}/api/results/history`)
    if (!r.ok) return
    setHistory(await r.json())
  }

  async function loadLogSessions() {
    const r = await fetch(`${API_BASE}/api/logs/sessions`)
    if (!r.ok) return
    const data = await r.json()
    setLogSessions(data)
    if (!selectedLogSessionId && data.length) setSelectedLogSessionId(data[0].id)
  }

  async function loadLogSessionDetail(sessionId) {
    if (!sessionId) return
    const r = await fetch(`${API_BASE}/api/logs/sessions/${sessionId}`)
    if (!r.ok) return
    setLogSessionDetail(await r.json())
  }

  async function clearLogsHistory() {
    if (!clearLogsPassword.trim()) {
      notify('warning', 'Informe a senha para limpar logs.')
      return
    }
    const r = await fetch(`${API_BASE}/api/logs/clear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: clearLogsPassword }),
    })
    if (!r.ok) {
      const e = await r.json()
      notify('error', e.detail || 'Falha ao limpar logs.')
      return
    }
    setClearLogsPassword('')
    setSelectedLogSessionId('')
    setLogSessionDetail(null)
    setLogSessions([])
    notify('success', 'Logs limpos com sucesso.')
  }

  useEffect(() => {
    loadLogSessionDetail(selectedLogSessionId)
  }, [selectedLogSessionId])

  async function onPickFile(evt) {
    const selected = evt.target.files?.[0]
    if (!selected) return
    setFile(selected)
    const formData = new FormData()
    formData.append('file', selected)
    const r = await fetch(`${API_BASE}/api/preview`, { method: 'POST', body: formData })
    if (!r.ok) {
      notify('error', 'Arquivo inválido. Envie .xlsx ou .xls.')
      return
    }
    setPreview(await r.json())
    notify('success', 'Planilha carregada com sucesso.')
  }

  function clearFile() {
    setFile(null)
    setPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function notify(type, message) {
    setToast({ type, message })
  }

  function validateConfigForStart() {
    const missing = {}
    if (!String(config.login || '').trim()) missing.login = true
    if (!String(config.senha || '').trim()) missing.senha = true
    setConfigErrors(missing)
    return Object.keys(missing).length === 0
  }

  async function saveConfig() {
    setBusyAction('save')
    try {
      const r = await fetch(`${API_BASE}/api/config`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config),
      })
      if (!r.ok) throw new Error('Falha ao salvar configurações.')
      notify('success', 'Configurações salvas com sucesso.')
    } catch (err) {
      notify('error', err.message || 'Falha ao salvar configurações.')
    } finally {
      setBusyAction('')
    }
  }

  async function startJob() {
    const hasConfig = validateConfigForStart()
    if (!hasConfig) {
      setActiveMenu('Processamento')
      configCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      loginInputRef.current?.focus()
      notify('warning', 'Preencha as configurações obrigatórias (Login e Senha) antes de iniciar.')
      return
    }
    if (!file) {
      notify('warning', 'Selecione uma planilha antes de iniciar.')
      return
    }
    setLoading(true)
    setBusyAction('start')
    setLogs([])
    const fd = new FormData()
    fd.append('file', file)
    fd.append('login', config.login)
    fd.append('senha', config.senha)
    fd.append('atraso_fases', String(config.atraso_fases))
    fd.append('atraso_etapas', String(config.atraso_etapas))
    fd.append('dados_km', config.dados_km)
    fd.append('aceitar_frete_minimo_antt', String(config.aceitar_frete_minimo_antt))

    const r = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: fd })
    const data = await r.json()
    if (!r.ok) {
      notify('error', data.detail || 'Erro ao iniciar automação.')
      setLoading(false)
      setBusyAction('')
      return
    }
    setJobId(data.job_id)
    setJob(data.status)
    notify('success', 'Automação iniciada com sucesso.')
    setLoading(false)
    setBusyAction('')
  }

  async function doPauseResume() {
    if (!jobId || !job) return
    const route = job.state === 'paused' ? 'resume' : 'pause'
    setBusyAction(route)
    try {
      const r = await fetch(`${API_BASE}/api/jobs/${jobId}/${route}`, { method: 'POST' })
      if (!r.ok) throw new Error(`Falha ao ${route === 'pause' ? 'pausar' : 'retomar'} automação.`)
      notify('info', route === 'pause' ? 'Automação pausada.' : 'Automação retomada.')
    } catch (err) {
      notify('error', err.message || 'Falha ao alterar status da automação.')
    } finally {
      setBusyAction('')
    }
  }

  async function stopJob() {
    if (!jobId) return
    if (!window.confirm('Deseja realmente parar a automação atual?')) return
    setBusyAction('stop')
    try {
      const r = await fetch(`${API_BASE}/api/jobs/${jobId}/stop`, { method: 'POST' })
      if (!r.ok) throw new Error('Falha ao parar automação.')
      notify('warning', 'Automação encerrada pelo usuário.')
    } catch (err) {
      notify('error', err.message || 'Falha ao parar automação.')
    } finally {
      setBusyAction('')
    }
  }

  async function deleteSelected() {
    if (!selectedResults.length) {
      notify('warning', 'Selecione ao menos um registro para excluir.')
      return
    }
    if (!deletePassword.trim()) {
      notify('warning', 'Informe a senha para excluir registros.')
      return
    }
    if (!window.confirm(`Confirma exclusão de ${selectedResults.length} registro(s)?`)) return
    setBusyAction('delete')
    const r = await fetch(`${API_BASE}/api/results/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: selectedResults, password: deletePassword }),
    })
    if (!r.ok) {
      const e = await r.json()
      setBusyAction('')
      notify('error', e.detail || 'Falha ao excluir registros.')
      return
    }
    setSelectedResults([])
    setDeletePassword('')
    await loadHistory()
    setBusyAction('')
    notify('success', 'Registros excluídos com sucesso.')
  }

  function updateConfig(field, value) {
    setConfig((old) => ({ ...old, [field]: value }))
    setConfigErrors((prev) => ({ ...prev, [field]: false }))
  }

  function toggleSelected(id) {
    setSelectedResults((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  function renderProcessamento() {
    return (
      <>
        <section className="grid-2">
          <article className="card">
            <div className="card-head"><h3>Arquivo</h3></div>
            <label className="file-zone">
              <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={onPickFile} />
              <span>{file ? 'Trocar planilha' : 'Selecionar planilha'}</span>
            </label>
            <div className="file-meta-row">
              <p className="muted">{preview ? `${preview.rows} linhas, ${preview.cols} colunas` : '0 linhas, 0 colunas'}</p>
              {file && <button className="ghost danger-outline" onClick={clearFile}>Remover planilha</button>}
            </div>
            {file && <p className="muted filename-inline">{file.name} <button className="mini-x" onClick={clearFile}>×</button></p>}
          </article>

          <article className={`card ${Object.values(configErrors).some(Boolean) ? 'card-highlight' : ''}`} ref={configCardRef}>
            <div className="card-head"><h3>Configurações</h3></div>
            <div className="form-grid">
              <label>Login LogTudo<input ref={loginInputRef} className={configErrors.login ? 'field-error' : ''} value={config.login} onChange={(e) => updateConfig('login', e.target.value)} /></label>
              <label>
                Senha LogTudo
                <div className="password-field-wrap">
                  <input className={configErrors.senha ? 'field-error' : ''} type={showPassword ? 'text' : 'password'} value={config.senha} onChange={(e) => updateConfig('senha', e.target.value)} />
                  <button type="button" className="toggle-pass-btn" onClick={() => setShowPassword((p) => !p)}>{showPassword ? 'Ocultar' : 'Mostrar'}</button>
                </div>
              </label>
              <label>Atraso entre fases (s)<input type="number" step="0.1" value={config.atraso_fases} onChange={(e) => updateConfig('atraso_fases', Number(e.target.value))} /></label>
              <label>Atraso entre etapas (s)<input type="number" step="0.1" value={config.atraso_etapas} onChange={(e) => updateConfig('atraso_etapas', Number(e.target.value))} /></label>
              <label>KM padrão<input value={config.dados_km} onChange={(e) => updateConfig('dados_km', e.target.value)} /></label>
              <label className="toggle-row">Aceitar frete mínimo ANTT<input type="checkbox" checked={config.aceitar_frete_minimo_antt} onChange={(e) => updateConfig('aceitar_frete_minimo_antt', e.target.checked)} /></label>
            </div>
            <div className="config-actions-row"><button className="secondary" onClick={saveConfig} disabled={busyAction === 'save'}>{busyAction === 'save' ? 'Salvando...' : 'Salvar Configurações'}</button></div>
          </article>
        </section>

        <section className="card">
          <div className="card-head"><h3>Pré-visualização</h3></div>
          <div className="preview-table">
            {preview?.preview?.length ? (
              <table>
                <thead><tr>{preview.headers.map((h, i) => <th key={i}>{h || `col_${i + 1}`}</th>)}</tr></thead>
                <tbody>{preview.preview.map((row, idx) => <tr key={idx}>{Object.keys(row).map((k) => <td key={k}>{String(row[k] ?? '')}</td>)}</tr>)}</tbody>
              </table>
            ) : <p className="muted">Sem dados para pré-visualizar.</p>}
          </div>
        </section>

        <section className="card">
          <div className="card-head"><h3>Controle</h3><span>{progress}%</span></div>
          <div className="control-row">
            <button className="primary" onClick={startJob} disabled={loading || busyAction === 'start'}>{busyAction === 'start' ? 'Iniciando...' : 'Iniciar'}</button>
            <button className="secondary" onClick={doPauseResume} disabled={!jobId || busyAction === 'pause' || busyAction === 'resume'}>{busyAction === 'pause' || busyAction === 'resume' ? 'Aguarde...' : (job?.state === 'paused' ? 'Continuar' : 'Pausar')}</button>
            <button className="danger" onClick={stopJob} disabled={!jobId || busyAction === 'stop'}>{busyAction === 'stop' ? 'Parando...' : 'Parar'}</button>
          </div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
          <p className="muted">{job ? `${job.current_item} de ${job.total_items} | fase ${job.current_phase}` : '0 de 0'}{job?.state ? ` | status: ${job.state}` : ''}</p>
        </section>

        <section className="card logs-card">
          <div className="card-head">
            <h3>Logs ao vivo</h3>
            <div className="inline-actions">
              <select value={filter} onChange={(e) => setFilter(e.target.value)}>{LEVELS.map((lv) => <option key={lv}>{lv}</option>)}</select>
              <button className="ghost" onClick={() => setLogs([])}>Limpar</button>
              <label className="toggle-inline"><input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />Auto-scroll</label>
            </div>
          </div>
          <div className="logs-box" ref={logsRef}>
            {filteredLogs.map((log) => <div className={`log-row lv-${log.level}`} key={log.seq}>[{log.timestamp}] [{log.level}] {log.message}</div>)}
          </div>
        </section>
      </>
    )
  }

  function renderResultados() {
    return (
      <>
        <section className="grid-2 metrics-grid">
          <article className="card metric-card"><h4>Sucessos</h4><strong>{metrics.sucessos}</strong></article>
          <article className="card metric-card"><h4>Erros</h4><strong>{metrics.erros}</strong></article>
          <article className="card metric-card"><h4>Pendentes</h4><strong>{metrics.pendentes}</strong></article>
          <article className="card metric-card"><h4>Taxa</h4><strong>{metrics.taxa}%</strong></article>
        </section>

        <section className="card">
          <div className="card-head"><h3>Histórico de Planilhas</h3>
            <div className="inline-actions">
              <input placeholder="Senha para excluir" type="password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} />
              <button className="danger" onClick={deleteSelected} disabled={busyAction === 'delete'}>{busyAction === 'delete' ? 'Excluindo...' : 'Excluir selecionados'}</button>
            </div>
          </div>
          <div className="preview-table history-table-wrap">
            <table>
              <thead>
                <tr>
                  <th></th><th>Arquivo</th><th>Job</th><th>Status</th><th>Sucessos</th><th>Erros</th><th>Criado em</th><th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.id}>
                    <td><input type="checkbox" checked={selectedResults.includes(row.id)} onChange={() => toggleSelected(row.id)} /></td>
                    <td>{row.arquivo_original}</td>
                    <td>{row.job_id}</td>
                    <td>{row.status}</td>
                    <td>{row.sucessos ?? 0}</td>
                    <td>{row.erros ?? 0}</td>
                    <td>{row.created_at}</td>
                    <td>{row.result_file ? <a className="secondary download-link" href={`${API_BASE}/api/results/history/${row.id}/download`}>Download</a> : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </>
    )
  }

  function renderLogsOnly() {
    const rows = logsTab === 'acoes'
      ? (logSessionDetail?.acoes_criticas || [])
      : logsTab === 'passos'
        ? (logSessionDetail?.passos_acoes || [])
        : logsTab === 'artefatos'
          ? (logSessionDetail?.artefatos || [])
          : (logSessionDetail?.browser_logs || [])

    return (
      <section className="card logs-hub-card">
        <div className="card-head logs-hub-head">
          <h3>Central de Logs</h3>
          <div className="inline-actions logs-actions-top">
            <input
              placeholder="Senha para limpar logs"
              type="password"
              value={clearLogsPassword}
              onChange={(e) => setClearLogsPassword(e.target.value)}
            />
            <button className="danger" onClick={clearLogsHistory}>Limpar logs</button>
          </div>
        </div>

        <div className="logs-layout">
          <aside className="logs-sessions-list">
            <p className="muted">IDs (clique para copiar e carregar)</p>
            {logSessions.map((item) => (
              <button
                key={item.id}
                className={`session-id-btn ${selectedLogSessionId === item.id ? 'active' : ''}`}
                onClick={async () => {
                  await navigator.clipboard.writeText(item.id)
                  setSelectedLogSessionId(item.id)
                  notify('info', `ID ${item.id} copiado.`)
                }}
              >
                {item.id}
              </button>
            ))}
          </aside>

          <div className="logs-main-view">
            <div className="logs-tab-strip">
              <button className={`ghost ${logsTab === 'acoes' ? 'tab-active' : ''}`} onClick={() => setLogsTab('acoes')}>Ações críticas</button>
              <button className={`ghost ${logsTab === 'passos' ? 'tab-active' : ''}`} onClick={() => setLogsTab('passos')}>Passos e Ações</button>
              <button className={`ghost ${logsTab === 'artefatos' ? 'tab-active' : ''}`} onClick={() => setLogsTab('artefatos')}>Artefatos</button>
              <button className={`ghost ${logsTab === 'browser' ? 'tab-active' : ''}`} onClick={() => setLogsTab('browser')}>Log do Browser</button>
            </div>

            <div className="logs-meta-row">
              <span>ID: <strong>{logSessionDetail?.id || '-'}</strong></span>
              <span>Usuário: <strong>{logSessionDetail?.user || '-'}</strong></span>
              <span>IP: <strong>{logSessionDetail?.ip || '-'}</strong></span>
            </div>

            <div className="logs-box" ref={logsRef}>
              {rows.map((row, idx) => (
                <div className={`log-row lv-${row.level || 'INFO'}`} key={row.seq || row.path || idx}>
                  {logsTab === 'artefatos'
                    ? `${row.name} | ${row.path}`
                    : `[${row.timestamp}] ${row.level ? `[${row.level}] ` : ''}${row.message || row.path || ''}`}
                </div>
              ))}
              {!rows.length && <div className="muted">Sem dados para esta aba no ID selecionado.</div>}
            </div>
          </div>
        </div>
      </section>
    )
  }

  function renderManual() {
    return (
      <section className="card manual-card">
        <div className="card-head">
          <h3>Manual do Usuário</h3>
          <span className="muted">Guia rápido e detalhado para operação completa</span>
        </div>

        <article className="manual-section manual-prep">
          <div className="manual-headline"><h4>1. 🚀 Antes de começar</h4><span className="manual-tag">Preparação</span></div>
          <ol>
            <li>Tenha em mãos seu login e senha do LogTudo.</li>
            <li>Separe a planilha de entrada em formato `.xlsx` ou `.xls`.</li>
            <li>Revise os dados da planilha para evitar linhas incompletas.</li>
          </ol>
        </article>

        <article className="manual-section manual-config">
          <div className="manual-headline"><h4>2. 🔐 Primeiro acesso e configurações</h4><span className="manual-tag">Configuração</span></div>
          <ol>
            <li>Entre na tela <strong>Processamento</strong>.</li>
            <li>No cartão <strong>Configurações</strong>, preencha Login e Senha.</li>
            <li>Ajuste os atrasos apenas se necessário (padrão costuma funcionar bem).</li>
            <li>Defina o KM padrão e marque/desmarque a opção de frete mínimo ANTT.</li>
            <li>Clique em <strong>Salvar Configurações</strong>.</li>
          </ol>
          <p className="muted">Dica: faça esse passo uma vez e só altere quando houver mudança operacional.</p>
        </article>

        <article className="manual-section manual-input">
          <div className="manual-headline"><h4>3. 📄 Carregando planilha</h4><span className="manual-tag">Entrada de Dados</span></div>
          <ol>
            <li>No cartão <strong>Arquivo</strong>, clique em <strong>Selecionar planilha</strong>.</li>
            <li>Escolha o arquivo e aguarde a pré-visualização aparecer.</li>
            <li>Confira total de linhas e colunas antes de iniciar.</li>
            <li>Se enviou arquivo errado, use <strong>Remover planilha</strong> ou <strong>Trocar planilha</strong>.</li>
          </ol>
        </article>

        <article className="manual-section manual-run">
          <div className="manual-headline"><h4>4. ⚙️ Executando a automação</h4><span className="manual-tag">Execução</span></div>
          <ol>
            <li>Clique em <strong>Iniciar</strong>.</li>
            <li>Acompanhe o progresso no bloco <strong>Controle</strong>.</li>
            <li>Use <strong>Pausar</strong> para interromper temporariamente.</li>
            <li>Use <strong>Continuar</strong> para retomar do ponto atual.</li>
            <li>Use <strong>Parar</strong> apenas quando precisar encerrar a execução.</li>
          </ol>
        </article>

        <article className="manual-section manual-monitor">
          <div className="manual-headline"><h4>5. 📡 Lendo os logs (tela Logs)</h4><span className="manual-tag">Monitoramento</span></div>
          <ol>
            <li>Abra o menu <strong>Logs</strong> para foco total no monitoramento.</li>
            <li>Filtre por nível (`INFO`, `AVISO`, `ERRO`, etc.) para investigar mais rápido.</li>
            <li>Ative/desative <strong>Auto-scroll</strong> conforme sua análise.</li>
            <li>Use <strong>Limpar</strong> quando quiser uma leitura nova e organizada.</li>
          </ol>
          <p className="muted">Em caso de falha, procure primeiro por mensagens de nível <strong>ERRO</strong>.</p>
        </article>

        <article className="manual-section manual-results">
          <div className="manual-headline"><h4>6. 📊 Consultando resultados</h4><span className="manual-tag">Resultados</span></div>
          <ol>
            <li>Abra o menu <strong>Resultados</strong>.</li>
            <li>Veja os indicadores: Sucessos, Erros, Pendentes e Taxa.</li>
            <li>No histórico, localize o arquivo desejado.</li>
            <li>Clique em <strong>Download</strong> para baixar o resultado quando disponível.</li>
          </ol>
        </article>

        <article className="manual-section manual-security">
          <div className="manual-headline"><h4>7. 🧹 Exclusão de históricos</h4><span className="manual-tag">Segurança</span></div>
          <ol>
            <li>Marque as linhas que deseja excluir.</li>
            <li>Digite a senha no campo de exclusão.</li>
            <li>Clique em <strong>Excluir selecionados</strong>.</li>
          </ol>
          <p className="muted">A exclusão é uma ação sensível. Revise os itens marcados antes de confirmar.</p>
        </article>

        <article className="manual-section manual-support">
          <div className="manual-headline"><h4>8. 🛠️ Problemas comuns e solução rápida</h4><span className="manual-tag">Suporte</span></div>
          <ul>
            <li><strong>Arquivo inválido:</strong> confirme se é `.xlsx` ou `.xls`.</li>
            <li><strong>Não inicia:</strong> verifique se planilha, login e senha estão preenchidos.</li>
            <li><strong>Resultado sem download:</strong> aguarde conclusão do job ou veja erros nos logs.</li>
            <li><strong>Muitos erros:</strong> revise a qualidade dos dados na planilha de origem.</li>
          </ul>
        </article>
      </section>
    )
  }

  return (
    <>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
      {isManualPage ? (
        <main className="content manual-standalone">
          <header className="topbar">
            <div><h2>Manual do Usuário</h2><p>Guia ilustrativo para uso completo da aplicação.</p></div>
          </header>
          {renderManual()}
        </main>
      ) : (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="logo">LT</div><div><h1>LogTudo</h1><p>Automação de contratos</p></div></div>
        {MENU_ITEMS.map((item) => (
          <button
            key={item}
            className={`menu-btn ${activeMenu === item ? 'active' : ''}`}
            onClick={() => {
              if (item === 'Manual') {
                window.open(withBasePath('/manual/index.html'), '_blank', 'noopener,noreferrer')
                return
              }
              setActiveMenu(item)
            }}
          >
            {item}
          </button>
        ))}
        <div className="sidebar-status"><span>{job?.state || 'desconectado'}</span></div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div><h2>Contratos de Frete</h2><p>Operação central com logs em tempo real.</p></div>
          <div className="top-actions"><button className="ghost" onClick={() => setActiveMenu('Logs')}>Mostrar Logs</button><button className="primary" onClick={startJob} disabled={loading || busyAction === 'start'}>{busyAction === 'start' ? 'Iniciando...' : 'Iniciar'}</button></div>
        </header>

        {activeMenu === 'Resultados' && renderResultados()}
        {activeMenu === 'Logs' && renderLogsOnly()}
        {activeMenu === 'Processamento' && renderProcessamento()}
      </main>
    </div>
      )}
    </>
  )
}
