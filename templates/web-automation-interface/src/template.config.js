export const templateConfig = {
  brand: {
    organization: 'Sua Empresa',
    product: 'Automação Web',
    version: '1.0',
    logoUrl: '',
  },
  navigation: [
    { id: 'execution', label: 'Execução' },
    { id: 'history', label: 'Histórico' },
    { id: 'admin', label: 'Admin' },
  ],
  phases: [
    { id: 'F1', title: 'Leitura', subtitle: 'Entrada e validação' },
    { id: 'F2', title: 'Acesso', subtitle: 'Login no sistema' },
    { id: 'F3', title: 'Busca', subtitle: 'Localização do registro' },
    { id: 'F4', title: 'Preenchimento', subtitle: 'Dados operacionais' },
    { id: 'F5', title: 'Conclusão', subtitle: 'Gravação e evidências' },
  ],
  upload: {
    title: 'Arquivo de entrada',
    help: 'Arraste ou selecione o arquivo que alimentará a automação.',
    accept: '.xlsx,.xls,.csv',
  },
  credentials: [
    { key: 'username', label: 'Usuário', type: 'text', required: true },
    { key: 'password', label: 'Senha', type: 'password', required: true },
  ],
  operationalSettings: [
    { key: 'throttleSeconds', label: 'Intervalo entre itens (s)', type: 'number', defaultValue: 2.5, min: 0 },
    { key: 'headless', label: 'Executar navegador em segundo plano', type: 'checkbox', defaultValue: true },
  ],
}
