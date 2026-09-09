import React, { useEffect, useRef, useState } from 'react'
import Sidebar from './components/Sidebar'
import ScreenshotModal from './components/ScreenshotModal'
import TabAdmin from './components/TabAdmin'
import TabEmissao from './components/TabEmissao'
import TabHistorico from './components/TabHistorico'
import Toast from './components/Toast'
import { ThemeProvider } from './context/ThemeContext'
import { api } from './services/api'
import { JobSocket } from './services/websocket'

export default function App() {
  const [activeTab, setActiveTab] = useState('emissao')
  const [config, setConfig] = useState(() => {
    try {
      const saved = localStorage.getItem('logtudo_config')
      return saved
        ? JSON.parse(saved)
        : {
            login: '',
            senha: '',
            atraso_fases: 2.5,
            dados_km: '20',
            aceitar_frete_minimo_antt: true,
          }
    } catch (e) {
      return {
        login: '',
        senha: '',
        atraso_fases: 2.5,
        dados_km: '20',
        aceitar_frete_minimo_antt: true,
      }
    }
  })

  const [jobs, setJobs] = useState([])
  const [currentJob, setCurrentJob] = useState(null)
  const [jobItems, setJobItems] = useState([])
  const [logs, setLogs] = useState([])
  const [activeItem, setActiveItem] = useState(null)
  const [currentPhase, setCurrentPhase] = useState('F1')
  const [isProcessing, setIsProcessing] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [preValidationReport, setPreValidationReport] = useState(null)

  const [selectedJobDetail, setSelectedJobDetail] = useState(null)
  const [screenshotModalUrl, setScreenshotModalUrl] = useState(null)
  const [toast, setToast] = useState(null)

  const socketRef = useRef(null)

  const showToast = (message, type = 'info') => {
    setToast({ message, type, id: Date.now() })
  }

  useEffect(() => {
    const initApp = async () => {
      try {
        await loadJobs()
        const cfg = await api.getConfig()
        if (cfg && Object.keys(cfg).length > 0) {
          setConfig((prev) => ({ ...prev, ...cfg }))
        }
        setIsConnected(true)
      } catch (e) {
        console.error('Falha ao conectar com o backend:', e)
        setIsConnected(false)
      }
    }
    initApp()
  }, [])

  const loadJobs = async () => {
    try {
      const res = await api.listJobs(100, 0)
      setJobs(res.jobs || [])
      return res.jobs || []
    } catch (e) {
      console.error('Erro ao listar jobs:', e)
      return []
    }
  }

  // Detecta job em execução no startup (recuperação de sessão)
  useEffect(() => {
    const running = jobs.find((j) => j.status === 'RUNNING' || j.status === 'PAUSED')
    if (running && !currentJob) {
      setCurrentJob(running)
    }
  }, [jobs])

  // Polling de fallback quando processando
  useEffect(() => {
    if (!currentJob?.id) return
    const interval = setInterval(async () => {
      try {
        const details = await api.getJob(currentJob.id)
        if (details?.job) {
          setCurrentJob(details.job)
          setJobItems(details.items || [])
          if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(details.job.status)) {
            setIsProcessing(false)
            setIsPaused(false)
            loadJobs()
          } else if (details.job.status === 'PAUSED') {
            setIsPaused(true)
          } else if (details.job.status === 'RUNNING') {
            setIsProcessing(true)
            setIsPaused(false)
          }
        }

        if (!isConnected) {
          const logsData = await api.getJobLogs(currentJob.id)
          if (logsData?.logs) {
            setLogs(logsData.logs)
            const lastLog = logsData.logs[logsData.logs.length - 1]
            if (lastLog?.phase && lastLog.phase.startsWith('F')) {
              setCurrentPhase(lastLog.phase)
            }
          }
        }
      } catch (e) {}
    }, 1500)

    return () => clearInterval(interval)
  }, [currentJob?.id, isConnected])

  // WebSocket para o job ativo
  useEffect(() => {
    if (!currentJob?.id) {
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      return
    }

    const onEvent = (event) => {
      if (event.type === 'connection') {
        setIsConnected(event.status === 'connected')
      } else if (event.type === 'log') {
        setLogs((prev) => [...prev, event.data])
        if (event.data.phase && event.data.phase.startsWith('F')) {
          setCurrentPhase(event.data.phase)
        }
      } else if (event.type === 'progress') {
        if (event.data.current_item) {
          setActiveItem(event.data.current_item)
        }
        if (event.data.status === 'RUNNING') {
          setIsProcessing(true)
          setIsPaused(false)
        }
      }
    }

    const onError = () => setIsConnected(false)

    socketRef.current = new JobSocket(currentJob.id, onEvent, onError)

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
    }
  }, [currentJob?.id])

  const handleUploadAndValidate = async (file) => {
    try {
      const report = await api.uploadAndValidate(file)
      setPreValidationReport(report)
      setCurrentJob({ id: report.job_id, total_items: report.total_rows, success_count: 0, error_count: 0 })
      setLogs([])
      setJobItems([])
      showToast(`Planilha ${report.filename} validada com sucesso!`, 'success')
      loadJobs()
    } catch (e) {
      showToast(`Erro na validação: ${e.message}`, 'error')
      throw e
    }
  }

  const handleStartJob = async (jobId, payload) => {
    try {
      await api.startJob(jobId, payload)
      setIsProcessing(true)
      setIsPaused(false)
      showToast(`Execução do lote ${jobId} iniciada!`, 'success')
    } catch (e) {
      showToast(`Falha ao iniciar: ${e.message}`, 'error')
    }
  }

  const handlePauseJob = async () => {
    if (!currentJob?.id) return
    try {
      await api.pauseJob(currentJob.id)
      setIsPaused(true)
      showToast('Pausa solicitada. Aguardando conclusão do item atual...', 'warning')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleResumeJob = async () => {
    if (!currentJob?.id) return
    try {
      await api.resumeJob(currentJob.id)
      setIsPaused(false)
      showToast('Execução retomada!', 'success')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleCancelJob = async () => {
    if (!currentJob?.id) return
    try {
      await api.cancelJob(currentJob.id)
      setIsProcessing(false)
      setIsPaused(false)
      showToast('Cancelamento do lote solicitado.', 'warning')
      loadJobs()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleSaveConfig = async (newConfig) => {
    setConfig(newConfig)
    try {
      localStorage.setItem('logtudo_config', JSON.stringify(newConfig))
      await api.saveConfig(newConfig)
    } catch (e) {}
  }

  const handleResetPreValidation = () => {
    setPreValidationReport(null)
    setCurrentJob(null)
    setJobItems([])
    setLogs([])
    setActiveItem(null)
    setCurrentPhase('F1')
    setIsProcessing(false)
    setIsPaused(false)
    loadJobs()
  }

  const handleSelectJobForDetail = async (jobId) => {
    try {
      const details = await api.getJob(jobId)
      setSelectedJobDetail(details)
    } catch (e) {
      showToast('Erro ao carregar detalhes do lote.', 'error')
    }
  }

  const hasActiveJob = currentJob && ['RUNNING', 'PAUSED'].includes(currentJob.status)

  return (
    <ThemeProvider>
      <div className="flex min-h-screen">
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isConnected={isConnected}
          currentJob={currentJob}
          isProcessing={isProcessing}
          isPaused={isPaused}
          progress={currentJob?.total_items ? (currentJob.success_count || 0) / currentJob.total_items : 0}
          activeItem={activeItem}
          onGoToJob={() => setActiveTab('emissao')}
        />

        <main className="flex-1 min-w-0 px-6 py-6 max-w-[1400px]">
          {activeTab === 'emissao' && (
            <TabEmissao
              config={config}
              currentJob={currentJob}
              jobItems={jobItems}
              logs={logs}
              activeItem={activeItem}
              currentPhase={currentPhase}
              isProcessing={isProcessing}
              isPaused={isPaused}
              hasActiveJob={hasActiveJob}
              onUploadAndValidate={handleUploadAndValidate}
              onStartJob={handleStartJob}
              onPauseJob={handlePauseJob}
              onResumeJob={handleResumeJob}
              onCancelJob={handleCancelJob}
              preValidationReport={preValidationReport}
              onResetPreValidation={handleResetPreValidation}
              onOpenScreenshot={setScreenshotModalUrl}
            />
          )}

          {activeTab === 'historico' && (
            <TabHistorico
              jobs={jobs}
              onSelectJobForDetail={handleSelectJobForDetail}
              selectedJobDetail={selectedJobDetail}
              onCloseDrawer={() => setSelectedJobDetail(null)}
              onOpenScreenshot={setScreenshotModalUrl}
            />
          )}

          {activeTab === 'admin' && (
            <TabAdmin
              jobs={jobs}
              config={config}
              onSaveConfig={handleSaveConfig}
              showToast={showToast}
            />
          )}
        </main>

        <ScreenshotModal
          isOpen={!!screenshotModalUrl}
          onClose={() => setScreenshotModalUrl(null)}
          imageUrl={screenshotModalUrl}
        />

        <Toast toast={toast} onClose={() => setToast(null)} />
      </div>
    </ThemeProvider>
  )
}
