const prefix = normalizePrefix(import.meta.env.VITE_API_BASE_URL || '')
const mockMode = import.meta.env.VITE_USE_MOCK_API !== 'false'
const wait = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms))

function normalizePrefix(value) {
  const trimmed = value.trim().replace(/\/$/, '')
  if (!trimmed || trimmed === '/') return ''
  return trimmed.startsWith('/') || /^https?:\/\//.test(trimmed) ? trimmed : `/${trimmed}`
}

async function request(path, options = {}) {
  const response = await fetch(`${prefix}${path}`, options)
  if (!response.ok) {
    let message = `Falha HTTP ${response.status}`
    try {
      const body = await response.json()
      message = body.detail || body.message || message
    } catch { /* resposta sem JSON */ }
    throw new Error(message)
  }
  const type = response.headers.get('content-type') || ''
  return type.includes('application/json') ? response.json() : response
}

const mockJobs = []
let mockConfig = { username: '', password: '', throttleSeconds: 2.5, headless: true }

function makeMockJob(file) {
  const stamp = new Date().toISOString().replace(/\D/g, '').slice(0, 14)
  return {
    id: `demo-${stamp}`,
    filename: file.name,
    status: 'PENDING',
    total_items: 8,
    success_count: 0,
    error_count: 0,
    invalid_count: 0,
    created_at: new Date().toISOString(),
    current_phase: 'F1',
    percent: 0,
    items: Array.from({ length: 8 }, (_, index) => ({
      id: `item-${index + 1}`,
      reference: `REG-${String(index + 1).padStart(4, '0')}`,
      status: 'PENDING',
      message: 'Aguardando processamento',
    })),
    logs: [],
    artifacts: [],
  }
}

export const api = {
  async health() {
    if (mockMode) return { status: 'ready', mode: 'demo' }
    return request('/health/ready')
  },
  async uploadAndValidate(file) {
    if (mockMode) {
      await wait()
      const job = makeMockJob(file)
      mockJobs.unshift(job)
      return { job_id: job.id, is_valid: true, filename: file.name, total_rows: 8, valid_rows_count: 8, invalid_rows_count: 0, preview: job.items.slice(0, 5) }
    }
    const body = new FormData()
    body.append('file', file)
    return request('/api/jobs/upload-and-validate', { method: 'POST', body })
  },
  async startJob(jobId, credentials) {
    if (mockMode) {
      const job = mockJobs.find((entry) => entry.id === jobId)
      if (job) job.status = 'RUNNING'
      return { success: true, job_id: jobId }
    }
    return request(`/api/jobs/${jobId}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    })
  },
  async action(jobId, action) {
    if (mockMode) {
      const job = mockJobs.find((entry) => entry.id === jobId)
      if (job) job.status = action === 'pause' ? 'PAUSED' : action === 'resume' ? 'RUNNING' : 'CANCELLED'
      return { success: true, job_id: jobId }
    }
    return request(`/api/jobs/${jobId}/${action}`, { method: 'POST' })
  },
  async listJobs() {
    if (mockMode) return { jobs: mockJobs }
    return request('/api/jobs?limit=100')
  },
  async getJob(jobId) {
    if (mockMode) {
      const job = mockJobs.find((entry) => entry.id === jobId)
      return { job, items: job?.items || [], artifacts: job?.artifacts || [] }
    }
    return request(`/api/jobs/${jobId}`)
  },
  async getConfig() {
    if (mockMode) return { ...mockConfig }
    return request('/api/config')
  },
  async saveConfig(config) {
    if (mockMode) {
      mockConfig = { ...config }
      return mockConfig
    }
    return request('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
  },
  downloadUrl(jobId, artifactId) {
    return `${prefix}/api/jobs/${encodeURIComponent(jobId)}/download/${encodeURIComponent(artifactId)}`
  },
  mockMode,
}
