/**
 * Cliente de API REST unificado para o Contratos_auto (FastAPI v2).
 */

const getApiBase = () => {
  if (typeof window !== 'undefined' && window.LOGTUDO_BASE_PATH) {
    return String(window.LOGTUDO_BASE_PATH).replace(/\/+$/, '')
  }
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    return String(import.meta.env.VITE_API_BASE_URL).replace(/\/+$/, '')
  }
  return ''
}

export const API_BASE = getApiBase()

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
    },
  })

  if (!response.ok) {
    let errorDetail = 'Erro na requisição'
    try {
      const errJson = await response.json()
      errorDetail = errJson.detail || errJson.message || errorDetail
    } catch (e) {
      errorDetail = await response.text()
    }
    throw new Error(errorDetail || `Status ${response.status}`)
  }

  return response.json()
}

export const api = {
  API_BASE,
  // Jobs & Upload
  uploadAndValidate: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request('/api/v2/jobs/upload-and-validate', {
      method: 'POST',
      body: formData,
    })
  },

  startJob: async (jobId, payload) => {
    return request(`/api/v2/jobs/${jobId}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  pauseJob: async (jobId) => {
    return request(`/api/v2/jobs/${jobId}/pause`, { method: 'POST' })
  },

  resumeJob: async (jobId) => {
    return request(`/api/v2/jobs/${jobId}/resume`, { method: 'POST' })
  },

  cancelJob: async (jobId) => {
    return request(`/api/v2/jobs/${jobId}/cancel`, { method: 'POST' })
  },

  getJob: async (jobId) => {
    return request(`/api/v2/jobs/${jobId}`)
  },

  listJobs: async (limit = 50, offset = 0) => {
    return request(`/api/v2/jobs?limit=${limit}&offset=${offset}`)
  },

  getJobLogs: async (jobId, level = null) => {
    const q = level && level !== 'TODOS' ? `?level=${level}` : ''
    return request(`/api/v2/jobs/${jobId}/logs${q}`)
  },

  getJobArtifacts: async (jobId) => {
    return request(`/api/v2/jobs/${jobId}/artifacts`)
  },

  getDownloadUrl: (jobId, artifactId) => {
    return `${API_BASE}/api/v2/jobs/${jobId}/download/${artifactId}`
  },

  // Config & Seletores
  getSelectorsConfig: async () => {
    return request('/api/v2/config/selectors')
  },

  getConfig: async () => {
    try {
      return await request('/api/config')
    } catch (e) {
      return {}
    }
  },

  saveConfig: async (config) => {
    return request('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
  },

  // Observabilidade & Admin
  getDebugArtifacts: async () => {
    return request('/api/debug/artifacts')
  },

  listLogSessions: async () => {
    return request('/api/logs/sessions')
  },

  getLogSession: async (id) => {
    return request(`/api/logs/sessions/${id}`)
  },

  clearLogs: async (password) => {
    return request('/api/logs/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
  },
}
