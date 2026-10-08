const apiPrefix = normalizePrefix(import.meta.env.VITE_API_BASE_URL || '')

function normalizePrefix(value) {
  const trimmed = value.trim().replace(/\/$/, '')
  if (!trimmed || trimmed === '/') return ''
  return trimmed.startsWith('/') || /^https?:\/\//.test(trimmed) ? trimmed : `/${trimmed}`
}

export function connectJobStream(jobId, handlers = {}) {
  if (!jobId || import.meta.env.VITE_USE_MOCK_API !== 'false') return () => {}

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const absoluteApi = /^https?:\/\//.test(apiPrefix)
  const wsBase = absoluteApi
    ? apiPrefix.replace(/^http/, 'ws')
    : `${protocol}//${window.location.host}${apiPrefix}`
  let socket
  let retryTimer
  let stopped = false
  let retries = 0

  const open = () => {
    socket = new WebSocket(`${wsBase}/ws/jobs/${encodeURIComponent(jobId)}`)
    socket.onopen = () => {
      retries = 0
      handlers.onConnection?.(true)
    }
    socket.onmessage = (event) => {
      try { handlers.onEvent?.(JSON.parse(event.data)) } catch { /* mensagem não estruturada */ }
    }
    socket.onerror = () => handlers.onConnection?.(false)
    socket.onclose = () => {
      handlers.onConnection?.(false)
      if (!stopped) retryTimer = window.setTimeout(open, Math.min(1000 * 2 ** retries++, 15000))
    }
  }

  open()
  return () => {
    stopped = true
    window.clearTimeout(retryTimer)
    socket?.close()
  }
}
