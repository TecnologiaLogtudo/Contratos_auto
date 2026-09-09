import React, { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function TabConfiguracoes({ config, onSaveConfig, showToast }) {
  const [formData, setFormData] = useState({ ...config })
  const [selectors, setSelectors] = useState(null)
  const [activeSelectorGroup, setActiveSelectorGroup] = useState('login')
  const [loadingSelectors, setLoadingSelectors] = useState(false)

  useEffect(() => {
    setFormData({ ...config })
  }, [config])

  useEffect(() => {
    loadSelectors()
  }, [])

  const loadSelectors = async () => {
    setLoadingSelectors(true)
    try {
      const data = await api.getSelectorsConfig()
      setSelectors(data)
    } catch (e) {
      showToast('Falha ao carregar catálogo de seletores', 'error')
    } finally {
      setLoadingSelectors(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSaveConfig(formData)
    showToast('Configurações salvas com sucesso!', 'success')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card-panel p-4">
        <h2 className="text-base font-bold text-[var(--text-main)] flex items-center gap-2">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Configurações Operacionais & Catálogo de Seletores
        </h2>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          Parâmetros de execução de scraping, rate limiting, credenciais e inspeção de seletores DOM
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Formulário de Parâmetros Operacionais */}
        <div className="lg:col-span-5 card-panel p-5 flex flex-col justify-between">
          <form onSubmit={handleSubmit} className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)] mb-3 pb-2 border-b border-[var(--border-subtle)]">
              Parâmetros de Automação
            </h3>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-muted)] mb-1">
                Intervalo entre cotações (Rate Limiting Throttle)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.5"
                  min="1.0"
                  max="15.0"
                  value={formData.atraso_fases || 2.5}
                  onChange={(e) => setFormData({ ...formData, atraso_fases: parseFloat(e.target.value) || 2.5 })}
                  className="input-field text-xs font-mono w-32"
                />
                <span className="text-xs text-[var(--text-muted)]">segundos (evita bloqueio no ERP)</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-muted)] mb-1">
                KM Padrão para Cálculo de Rota
              </label>
              <input
                type="text"
                value={formData.dados_km || '20'}
                onChange={(e) => setFormData({ ...formData, dados_km: e.target.value })}
                className="input-field text-xs font-mono"
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="chkAntt"
                checked={formData.aceitar_frete_minimo_antt !== false}
                onChange={(e) => setFormData({ ...formData, aceitar_frete_minimo_antt: e.target.checked })}
                className="rounded border-[var(--border-subtle)] text-[var(--color-primary)]"
              />
              <label htmlFor="chkAntt" className="text-xs text-[var(--text-main)] select-none">
                Aceitar confirmação automática de Frete Mínimo ANTT
              </label>
            </div>

            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)] pt-4 mb-2 pb-2 border-b border-[var(--border-subtle)]">
              Credenciais Padrão (e-Login)
            </h3>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-muted)] mb-1">
                Usuário Padrão
              </label>
              <input
                type="text"
                value={formData.login || ''}
                onChange={(e) => setFormData({ ...formData, login: e.target.value })}
                className="input-field text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-muted)] mb-1">
                Senha Padrão
              </label>
              <input
                type="password"
                value={formData.senha || ''}
                onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                className="input-field text-xs font-mono"
              />
            </div>

            <div className="pt-3">
              <button type="submit" className="w-full btn-primary justify-center">
                Salvar Configurações
              </button>
            </div>
          </form>
        </div>

        {/* Inspetor de Seletores DOM */}
        <div className="lg:col-span-7 card-panel p-5 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)] mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">
                Catálogo Centralizado de Seletores DOM
              </h3>
              <p className="text-[11px] text-[var(--text-muted)]">
                Isolamento total dos seletores de CSS/XPath do ERP LogTudo
              </p>
            </div>
            <button onClick={loadSelectors} className="btn-secondary text-xs py-1 px-2">
              Recarregar
            </button>
          </div>

          {/* Abas de Grupos de Seletores */}
          <div className="flex items-center gap-1.5 mb-4 overflow-x-auto pb-1">
            {['login', 'cotacoes', 'conhecimento', 'frete', 'contrato'].map((grp) => (
              <button
                key={grp}
                onClick={() => setActiveSelectorGroup(grp)}
                className={`px-3 py-1 rounded-md text-xs font-mono uppercase font-bold transition-all ${
                  activeSelectorGroup === grp
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'bg-[var(--bg-card-secondary)] text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                {grp}
              </button>
            ))}
          </div>

          {/* Tabela de Seletores */}
          <div className="flex-1 border border-[var(--border-subtle)] rounded-lg overflow-y-auto max-h-[380px] bg-[var(--terminal-bg)] p-3 font-mono text-xs">
            {loadingSelectors ? (
              <p className="text-slate-400 italic py-4 text-center">Carregando seletores...</p>
            ) : selectors && selectors[activeSelectorGroup] ? (
              <div className="space-y-2.5">
                {Object.entries(selectors[activeSelectorGroup]).map(([key, val]) => (
                  <div key={key} className="p-2 rounded bg-white/5 border border-white/5">
                    <span className="text-sky-400 font-bold block mb-1">{key}:</span>
                    <span className="text-emerald-300 break-all text-[11px]">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-400 italic py-4 text-center">Nenhum seletor encontrado.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
