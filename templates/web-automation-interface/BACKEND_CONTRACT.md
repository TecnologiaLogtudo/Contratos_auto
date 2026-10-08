# Contrato mínimo do backend

O cliente usa `VITE_API_BASE_URL` como prefixo. Se estiver vazio, as rotas abaixo são relativas ao mesmo host. Erros devem usar status HTTP adequado e `{ "detail": "mensagem acionável" }`.

## Saúde

`GET /health/ready`

```json
{ "status": "ready" }
```

## Arquivo e pré-validação

`POST /api/jobs/upload-and-validate` como `multipart/form-data`, campo `file`.

Resposta mínima:

```json
{
  "job_id": "300926-00001",
  "is_valid": true,
  "filename": "entrada.xlsx",
  "total_rows": 20,
  "valid_rows_count": 19,
  "invalid_rows_count": 1,
  "row_errors": [],
  "preview": []
}
```

## Execução

`POST /api/jobs/{job_id}/start`

```json
{
  "usuario": "operador",
  "senha": "segredo",
  "headless": true,
  "throttle_seconds": 2.5
}
```

`POST /api/jobs/{job_id}/pause`

`POST /api/jobs/{job_id}/resume`

`POST /api/jobs/{job_id}/cancel`

Resposta das ações:

```json
{ "success": true, "message": "Ação aceita", "job_id": "300926-00001" }
```

## Consulta durável

`GET /api/jobs?limit=100`

```json
{ "jobs": [{ "id": "300926-00001", "filename": "entrada.xlsx", "status": "RUNNING", "total_items": 20, "success_count": 7, "error_count": 0, "invalid_count": 1, "created_at": "2026-09-30T10:00:00" }] }
```

`GET /api/jobs/{job_id}`

```json
{
  "job": { "id": "300926-00001", "status": "RUNNING", "current_phase": "F3", "percent": 0.4 },
  "items": [{ "id": "item-1", "reference": "REG-0001", "status": "COMPLETED", "message": "Gravado" }],
  "artifacts": []
}
```

Estados esperados: `PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, `CANCELLED`.

## Configuração

`GET /api/config` e `PUT /api/config` com JSON. Nunca retorne senha em texto aberto numa aplicação multiusuário. Se a senha já existir, devolva somente um indicador como `password_configured: true`.

## Eventos ao vivo

`WS /ws/jobs/{job_id}`. Eventos recomendados:

```json
{ "type": "log", "data": { "timestamp": "10:01:02", "level": "INFO", "phase": "F3", "message": "Registro localizado" } }
```

```json
{ "type": "progress", "data": { "status": "RUNNING", "current_phase": "F3", "percent": 0.4, "success_count": 7, "total_items": 20 } }
```

O WebSocket acelera a UI, mas não substitui a persistência REST. Após reconexão, `GET /api/jobs/{job_id}` deve ser a fonte de verdade.

## Artefatos

Recomendado:

- `GET /api/jobs/{job_id}/artifacts`
- `GET /api/jobs/{job_id}/download/{artifact_id}`
- tipos: `EXCEL_RESULT`, `SCREENSHOT_ERROR`, `TRACE`, `JSON_EVIDENCE`;
- valide que o artefato pertence ao job antes do download;
- aplique retenção e limpeza por idade.

## Requisitos periféricos de produção

- banco persistente e transações por atualização de item;
- worker fora do event loop HTTP;
- healthcheck de prontidão;
- storage persistente para banco, uploads e artefatos;
- logs estruturados com job, fase, referência e nível;
- execução idempotente ou proteção contra início duplicado;
- política de CORS restrita em produção;
- limite de tamanho e validação real do arquivo enviado;
- tratamento de encerramento para marcar jobs interrompidos;
- segredos em variáveis protegidas ou secret manager.
