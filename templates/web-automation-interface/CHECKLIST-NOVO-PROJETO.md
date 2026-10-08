# Checklist para uma nova interface

## 1. Definir o contrato

- [ ] Nome do job/lote e do item do domínio.
- [ ] Arquivos aceitos e limite de tamanho.
- [ ] Campos obrigatórios e formato da pré-validação.
- [ ] Estados finais, retomáveis e canceláveis.
- [ ] Fases exibidas ao operador.

## 2. Personalizar a interface

- [ ] Editar `src/template.config.js`.
- [ ] Trocar título, marca e favicon.
- [ ] Ajustar colunas da tabela de itens.
- [ ] Definir quais credenciais ficam apenas em memória.
- [ ] Revisar mensagens e ações destrutivas.

## 3. Integrar o backend

- [ ] Implementar `BACKEND_CONTRACT.md`.
- [ ] Persistir job, itens, logs e artefatos.
- [ ] Rodar automação fora do event loop HTTP.
- [ ] Emitir progresso e logs estruturados.
- [ ] Impedir duas execuções incompatíveis ao mesmo tempo.

## 4. Preparar produção

- [ ] Definir `VITE_USE_MOCK_API=false`.
- [ ] Configurar base path e proxy reverso.
- [ ] Restringir CORS e proteger endpoints.
- [ ] Configurar volumes, backup e retenção.
- [ ] Adicionar healthcheck e desligamento gracioso.

## 5. Validar em rodadas

- [ ] Testar a interface em modo mock.
- [ ] Testar upload inválido e erros de API.
- [ ] Executar um item real com revisão humana.
- [ ] Executar um lote pequeno e conferir artefatos.
- [ ] Somente então liberar o lote normal.
