/**
 * Gerenciador híbrido de streaming (WebSocket com fallback automático para Server-Sent Events).
 */

import { API_BASE, api } from './api'

export class JobSocket {
  constructor(jobId, onEvent, onError) {
    this.jobId = jobId
    this.onEvent = onEvent || (() => {})
    this.onError = onError || (() => {})
    this.ws = null
    this.sse = null
    this.isClosedManually = false
    this.reconnectTimer = null
    this.wsFailures = 0
    this.connect()
  }

  getWsUrl() {
    const loc = window.location
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    let host = loc.host
    if (API_BASE && API_BASE.startsWith('http')) {
      const u = new URL(API_BASE)
      return `${u.protocol === 'https:' ? 'wss:' : 'ws:'}//${u.host}/ws/jobs/${this.jobId}`
    }
    return `${proto}//${host}${API_BASE}/ws/jobs/${this.jobId}`
  }

  getSseUrl() {
    return `${API_BASE}/api/v2/jobs/${this.jobId}/stream`
  }

  connect() {
    if (!this.jobId || this.isClosedManually) return

    // Se WebSocket falhou mais de 2 vezes consecutivas, usa SSE diretamente
    if (this.wsFailures >= 2) {
      this.connectSse()
      return
    }

    try {
      const url = this.getWsUrl()
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.wsFailures = 0
        this.onEvent({ type: 'connection', status: 'connected' })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onEvent(data)
        } catch (e) {
          console.error('[WS] Erro ao decodificar JSON:', e)
        }
      }

      this.ws.onclose = () => {
        this.wsFailures += 1
        this.onEvent({ type: 'connection', status: 'disconnected' })
        if (!this.isClosedManually) {
          if (this.wsFailures >= 2) {
            console.log('[WS] Alternando para fallback SSE (Server-Sent Events)...')
            this.connectSse()
          } else {
            this.reconnectTimer = setTimeout(() => this.connect(), 2000)
          }
        }
      }

      this.ws.onerror = (err) => {
        this.wsFailures += 1
        this.onError(err)
      }
    } catch (e) {
      this.wsFailures += 1
      this.connectSse()
    }
  }

  connectSse() {
    if (this.sse || this.isClosedManually) return
    try {
      const url = this.getSseUrl()
      this.sse = new EventSource(url)

      this.sse.onopen = () => {
        this.onEvent({ type: 'connection', status: 'connected' })
      }

      this.sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onEvent(data)
        } catch (e) {
          console.error('[SSE] Erro ao decodificar JSON:', e)
        }
      }

      this.sse.onerror = (err) => {
        this.onEvent({ type: 'connection', status: 'disconnected' })
        this.onError(err)
      }
    } catch (e) {
      this.onError(e)
    }
  }

  sendAction(action, payload = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, ...payload }))
    } else {
      // Fallback REST para ações quando conectado via SSE
      if (action === 'pause') api.pauseJob(this.jobId).catch(() => {})
      else if (action === 'resume') api.resumeJob(this.jobId).catch(() => {})
      else if (action === 'cancel') api.cancelJob(this.jobId).catch(() => {})
    }
  }

  close() {
    this.isClosedManually = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    if (this.sse) {
      this.sse.close()
      this.sse = null
    }
  }
}
