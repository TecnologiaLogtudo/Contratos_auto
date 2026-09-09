import React from 'react'
import { useTheme } from '../context/ThemeContext'

export default function Navbar({ activeTab, setActiveTab, historyCount = 0, isConnected = true }) {
  const { theme, toggleTheme } = useTheme()

  const tabs = [
    {
      id: 'emissao',
      label: 'Emissão de CTes',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
          <path d="m9 15 2 2 4-4" />
        </svg>
      ),
    },
    {
      id: 'historico',
      label: 'Histórico e Relatórios',
      badge: historyCount > 0 ? historyCount : null,
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 3v18h18" />
          <path d="m19 9-5 5-4-4-3 3" />
        </svg>
      ),
    },
    {
      id: 'config',
      label: 'Configurações e Seletores',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      ),
    },
    {
      id: 'admin',
      label: 'Observabilidade (Admin)',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      ),
    },
  ]

  return (
    <header className="w-full bg-[var(--bg-card)] border-b border-[var(--border-subtle)] sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        {/* Lado Esquerdo: Logo & Marca */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('emissao')}>
            <img
              src="/brand/logos/logo_logtudo.png"
              alt="LogTudo Logo"
              className="h-9 w-auto object-contain drop-shadow-sm"
              onError={(e) => {
                // Fallback se a imagem não carregar
                e.target.style.display = 'none'
              }}
            />
            <div className="flex flex-col">
              <span className="font-bold text-base tracking-tight text-[var(--text-main)] flex items-center gap-1.5">
                LogTudo <span className="font-light text-[var(--color-primary)]">Contratos</span>
              </span>
              <span className="text-[10px] text-[var(--text-muted)] font-mono tracking-wider">
                AUTOMAÇÃO v2.0
              </span>
            </div>
          </div>

          {/* Indicador de Status do Sistema */}
          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[var(--bg-card-secondary)] border border-[var(--border-subtle)] text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-amber-500 animate-pulse'
              }`}
            />
            <span className="text-[11px] font-medium text-[var(--text-muted)]">
              {isConnected ? 'Sistema Pronto' : 'Tentando Conectar...'}
            </span>
          </div>
        </div>

        {/* Centro: 4 Abas de Navegação */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all relative ${
                  isActive
                    ? 'bg-[var(--color-primary)] text-white shadow-sm'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-card-secondary)]'
                }`}
              >
                {tab.icon}
                <span className="hidden md:inline">{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      isActive ? 'bg-white/20 text-white' : 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Lado Direito: Tema & Perfil */}
        <div className="flex items-center gap-3">
          {/* Alternador de Tema */}
          <button
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Mudar para Tema Claro' : 'Mudar para Tema Escuro'}
            className="p-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:border-[var(--color-primary)] transition-all"
          >
            {theme === 'dark' ? (
              // Ícone Sol
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2" />
                <path d="M12 20v2" />
                <path d="m4.93 4.93 1.41 1.41" />
                <path d="m17.66 17.66 1.41 1.41" />
                <path d="M2 12h2" />
                <path d="M20 12h2" />
                <path d="m6.34 17.66-1.41 1.41" />
                <path d="m19.07 4.93-1.41 1.41" />
              </svg>
            ) : (
              // Ícone Lua
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
              </svg>
            )}
          </button>

          {/* Perfil Operador */}
          <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-[var(--border-subtle)]">
            <div className="w-8 h-8 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/30 flex items-center justify-center font-bold text-xs font-mono">
              OP
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-semibold text-[var(--text-main)] leading-tight">
                Operador Logística
              </span>
              <span className="text-[10px] text-[var(--text-dim)]">
                LogTudo Admin
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
