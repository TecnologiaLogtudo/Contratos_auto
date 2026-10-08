# Template de Interface para Automação Web

Template extraído dos padrões úteis do Contratos_auto, sem acoplamento à LogTudo ou ao domínio de CT-e. Entrega um painel React/Vite funcional em modo demonstração e um contrato de integração para backends de automação.

## O que já vem pronto

- shell responsivo com sidebar, status da API e tema claro/escuro;
- fluxo arquivo -> validação -> execução;
- credenciais e parâmetros dirigidos por configuração;
- fases, progresso, itens e terminal de logs;
- controles iniciar, pausar, continuar e cancelar;
- histórico pesquisável e visão administrativa;
- cliente REST, WebSocket com reconexão e URLs compatíveis com subcaminho;
- modo mock para desenvolver a interface antes do backend.

## Uso rápido

```bash
cp -R templates/web-automation-interface ../minha-interface
cd ../minha-interface
cp .env.example .env
npm install
npm run dev
```

O padrão `VITE_USE_MOCK_API=true` permite navegar e carregar qualquer `.xlsx`, `.xls` ou `.csv` sem backend. Para integrar:

1. Edite `src/template.config.js` com marca, fases, campos e parâmetros.
2. Implemente o contrato de `BACKEND_CONTRACT.md`.
3. Defina `VITE_USE_MOCK_API=false` e `VITE_API_BASE_URL`.
4. Rode `npm run build`.

## Pontos de extensão

- `src/template.config.js`: personalização sem tocar no fluxo principal.
- `src/services/api.js`: adaptação de payloads REST.
- `src/services/realtime.js`: streaming por WebSocket.
- `src/styles.css`: tokens semânticos e layout.
- `src/App.jsx`: composição das telas.

## Decisões herdadas da análise

- Job/lote é a unidade central da interface.
- Upload e validação acontecem antes de iniciar o robô.
- Estado durável vem do REST; eventos ao vivo vêm do WebSocket.
- A interface continua consultável após recarregar graças ao histórico do backend.
- Evidências e arquivos pertencem ao job e devem ser baixados por ID.
- A publicação deve suportar raiz e subcaminho sem URLs fixas.

## Limites intencionais

O template não inclui autenticação do próprio painel, autorização por perfil nem armazenamento seguro de segredos. O backend não deve devolver senhas em `GET /api/config`; em produção, prefira secret manager ou credenciais efêmeras. Confirmações destrutivas e políticas específicas do negócio também ficam para cada projeto.

Consulte `ANALISE-REFERENCIA.md` para o inventário coletado e `CHECKLIST-NOVO-PROJETO.md` para iniciar outra automação.
