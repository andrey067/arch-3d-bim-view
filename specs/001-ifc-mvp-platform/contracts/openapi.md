# API Contract — App 3D Viewer

**Feature**: `001-ifc-mvp-platform` (App 3D Viewer MVP)
**Status**: Contrato de superfície HTTP para o MVP.
**Geração**: OpenAPI auto-gerado pelo FastAPI na implementação; este
documento é a **especificação de superfície** que precede a geração
automática.

> **Sobre este contrato**: A stack é REST + JSON com OpenAPI
> auto-gerado. Este documento lista os endpoints, payloads e
> códigos de status do MVP. O conteúdo aqui é a **fonte da
> verdade** até a implementação produzir o OpenAPI equivalente.

---

## Convenções

- **Base URL**: `/api/v1`
- **Autenticação**: Bearer JWT (Access token) no header
  `Authorization: Bearer <access_token>` para endpoints privados.
  Endpoints marcados **[public]** não exigem auth.
- **Content-Type**: `application/json` (request e response) exceto
  onde explicitado.
- **Códigos de erro** (consistentes em toda a API):
  - `400` validação de payload
  - `401` sem token / token inválido / expirado
  - `403` autenticado mas sem permissão sobre o recurso
  - `404` recurso não encontrado
  - `409` conflito de estado (ex.: tentar retentar job que não é
    `failed`)
  - `413` payload grande demais (upload)
  - `415` formato não suportado / magic bytes inválidos
  - `422` invariante violada
  - `429` rate-limited
  - `500` erro inesperado
- **Identificadores**: UUID v4 em todos os IDs públicos.
- **Datas**: ISO-8601 UTC (`2026-06-11T13:45:00Z`).
- **Paginação**: cursor-based, parâmetros `?cursor=&limit=` (limite
  padrão 20, máximo 100).

---

## Recursos

### Auth — `/api/v1/auth`

#### `POST /api/v1/auth/register` — criar conta

Request:
```json
{
  "email": "user@example.com",
  "password": "string (>=8 chars)",
  "display_name": "string (opcional)"
}
```
Response `201`:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "string|null",
  "created_at": "iso8601"
}
```
Erros: `400` (email inválido), `409` (email já existe), `422`
(senha fraca).

#### `POST /api/v1/auth/login` — autenticar

Request:
```json
{ "email": "user@example.com", "password": "string" }
```
Response `200`:
```json
{
  "access_token": "jwt",
  "refresh_token": "opaque",
  "token_type": "Bearer",
  "expires_in": 900
}
```
Erros: `401` (credenciais inválidas), `429` (rate-limited).

#### `POST /api/v1/auth/refresh` — rotacionar tokens

Request:
```json
{ "refresh_token": "opaque" }
```
Response `200`: mesmo payload de `/login` (Access + novo Refresh;
o antigo é invalidado).

Erros: `401` (token inválido/expirado/revogado).

#### `POST /api/v1/auth/logout` — revogar refresh

Request:
```json
{ "refresh_token": "opaque" }
```
Response `204`. Idempotente.

---

### Projects — `/api/v1/projects`

#### `POST /api/v1/projects` — criar projeto

Request:
```json
{ "name": "string", "description": "string (opcional)" }
```
Response `201`: payload do projeto criado.

#### `GET /api/v1/projects` — listar projetos do owner

Query: `?archived=true&cursor=&limit=`

Response `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string|null",
      "latest_model_file": { "id": "uuid", "source_format": "ifc" } | null,
      "is_viewable": true,
      "created_at": "iso8601",
      "updated_at": "iso8601",
      "archived_at": "iso8601|null"
    }
  ],
  "next_cursor": "string|null"
}
```

#### `GET /api/v1/projects/{project_id}` — detalhe

Response `200`:
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string|null",
  "model_files": [ { "...": "ModelFile" } ],
  "share_links": [ { "...": "ShareLink" } ],
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "archived_at": "iso8601|null"
}
```

#### `PATCH /api/v1/projects/{project_id}` — atualizar nome/descrição

Request:
```json
{ "name": "string (opcional)", "description": "string (opcional)" }
```

#### `POST /api/v1/projects/{project_id}/archive` — arquivar
#### `POST /api/v1/projects/{project_id}/unarchive` — desarquivar
#### `DELETE /api/v1/projects/{project_id}` — remover definitivamente

`DELETE` remove o projeto, seus `ModelFile`s, todos os `ConversionJob`s
e todos os `ShareLink`s; remove os arquivos do storage.

---

### Model files — `/api/v1/projects/{project_id}/files`

#### `POST /api/v1/projects/{project_id}/files` — upload

Request: `multipart/form-data`
- `file`: binário do modelo (`ifc`/`dae`/`obj`/`glb`)
- `source_format`: enum (opcional — se ausente, detectado por magic
  bytes)

Response `202`:
```json
{
  "model_file_id": "uuid",
  "conversion_job_id": "uuid",
  "status": "pending"
}
```
Erros: `400` (payload), `404` (projeto), `409` (projeto arquivado),
`413` (limite de tamanho), `415` (formato não suportado / magic
bytes inválido).

#### `GET /api/v1/projects/{project_id}/files` — listar arquivos do projeto

Response `200`: lista de `ModelFile` (sem o binário).

#### `GET /api/v1/projects/{project_id}/files/{file_id}` — detalhe

Response `200`: payload de `ModelFile` (com metadados extraídos
quando o job estiver `ready`).

#### `DELETE /api/v1/projects/{project_id}/files/{file_id}` — remover

Remove o arquivo, o `ConversionJob` associado, e o GLB/thumbnail
produzido (se existirem).

---

### Conversion jobs — `/api/v1/jobs`

#### `GET /api/v1/jobs/{job_id}` — consultar status

Response `200`:
```json
{
  "id": "uuid",
  "model_file_id": "uuid",
  "status": "pending|running|ready|failed",
  "attempts": 0,
  "last_error": "string|null",
  "started_at": "iso8601|null",
  "finished_at": "iso8601|null",
  "duration_ms": 0,
  "glb_url": "string|null",
  "thumbnail_url": "string|null"
}
```

#### `POST /api/v1/jobs/{job_id}/retry` — retentar job `failed`

Cria um novo `ConversionJob` para o mesmo `ModelFile`.

Erros: `409` (job não está em `failed`).

---

### Share links — `/api/v1/projects/{project_id}/shares`

#### `POST /api/v1/projects/{project_id}/shares` — criar link

Request:
```json
{
  "model_file_id": "uuid"
}
```
Response `201`:
```json
{
  "id": "uuid",
  "token": "opaque-string",
  "url": "/s/{token}",
  "model_file_id": "uuid",
  "created_at": "iso8601"
}
```

#### `GET /api/v1/projects/{project_id}/shares` — listar

#### `POST /api/v1/shares/{token}/revoke` — revogar

(Idempotente; `204`.)

---

### Public share viewer — `/s`

Estes endpoints são **[public]**: autenticam pela posse do token, não
por JWT.

#### `GET /s/{token}` — **[public]** página de visualização

Retorna HTML renderizado pelo frontend (SPA). A página carrega o GLB
e o thumbnail via endpoints autenticados-por-token abaixo.

#### `GET /s/{token}/manifest` — **[public]** manifest do modelo

Response `200`:
```json
{
  "model_file_id": "uuid",
  "format": "glb",
  "glb_url": "/s/{token}/model.glb",
  "thumbnail_url": "/s/{token}/thumbnail.webp",
  "project_name": "string",
  "uploader_display_name": "string|null"
}
```

#### `GET /s/{token}/model.glb` — **[public]** binário do GLB

Response `200` com `Content-Type: model/gltf-binary`. Suporta HTTP
range requests.

#### `GET /s/{token}/thumbnail.webp` — **[public]** thumbnail

Response `200` com `Content-Type: image/webp`.

---

## Health

#### `GET /api/v1/health` — **[public]** liveness

Response `200`: `{ "status": "ok" }`

#### `GET /api/v1/health/ready` — **[public]** readiness

Verifica DB, Redis e storage. `200` se tudo saudável, `503` caso
contrário.

---

## Modelo JSON de superfície

### `User`
```json
{
  "id": "uuid",
  "email": "string",
  "display_name": "string|null",
  "created_at": "iso8601"
}
```

### `Project`
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string|null",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "archived_at": "iso8601|null"
}
```

### `ModelFile`
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "uploader_id": "uuid",
  "original_filename": "string",
  "source_format": "ifc|dae|obj|glb",
  "size_bytes": 0,
  "uploaded_at": "iso8601",
  "content_hash": "string (hex sha256)"
}
```

### `ConversionJob`
```json
{
  "id": "uuid",
  "model_file_id": "uuid",
  "status": "pending|running|ready|failed",
  "attempts": 0,
  "last_error": "string|null",
  "started_at": "iso8601|null",
  "finished_at": "iso8601|null",
  "duration_ms": 0,
  "glb_url": "string|null",
  "thumbnail_url": "string|null"
}
```

### `ShareLink`
```json
{
  "id": "uuid",
  "token": "opaque",
  "project_id": "uuid",
  "model_file_id": "uuid",
  "created_at": "iso8601",
  "revoked_at": "iso8601|null"
}
```

---

## Contrato interno: enfileiramento Celery

> O worker Celery é parte do mesmo processo Python
> (`apps/backend/app/conversion/`), portanto não há contrato HTTP
> entre backend e worker. Há, contudo, um **contrato de payload**
> via Celery.

**Task**: `conversion.process_model_file`

**Argumentos**:
```python
{
  "job_id": "uuid",
  "model_file_id": "uuid",
  "project_id": "uuid",
  "source_format": "ifc|dae|obj|glb",
  "original_storage_key": "string",
}
```

**Atualizações de estado** (escrita pelo worker, observável via
`GET /api/v1/jobs/{job_id}`):
- `pending → running`: marca `started_at`, incrementa `attempts`.
- `running → ready`: marca `finished_at`, popula `glb_storage_key`
  e `thumbnail_storage_key`, popula `duration_ms`.
- `running → failed`: marca `finished_at`, popula `last_error`,
  popula `duration_ms`.

**Idempotência**:
- Worker lê `ModelFile` e seu `ConversionJob`; antes de qualquer
  mutação, faz update condicional `WHERE status = 'pending' OR
  (status = 'failed' AND attempts < MAX_ATTEMPTS)`.
- Re-encoding: re-uploads criam um novo `ConversionJob`; o worker
  nunca sobrescreve artefatos de jobs anteriores.

---

## Headers de correlação

- Toda request aceita `X-Correlation-Id: <opaque>`. Se ausente, o
  backend gera um. O header é ecoado na response e propagado nos
  logs estruturados do worker.

---

## Limites do MVP (validados em zigue-zague no backend)

| Limite | Valor | Origem |
|---|---|---|
| Tamanho máximo de upload | `MAX_UPLOAD_MB` MB | Constante no core |
| Tentativas de processamento | `MAX_CONVERSION_ATTEMPTS` | Constante no core |
| Tamanho do access token | 15 min | Constante no core |
| Tamanho do refresh token | 30 dias (rotação) | Constante no core |
| Largura mínima de senha | 8 chars | Validação Pydantic |
| Rate limit auth | 10 req/min/IP | Middleware |

---

## Out of scope (sem endpoint no MVP)

Os itens abaixo **não** têm endpoint na API MVP e não devem ser
assumidos:
- Comentários em modelo
- Listagem/busca global de modelos de outros usuários
- Versionamento explícito
- Permissões granulares (roles)
- Métricas operacionais expostas
- Endpoints admin
- BIM tree / propriedades IFC
- `view_count` em ShareLink
- `metadata` extraído do modelo (vertex_count, material_count, etc.)
- `expires_at` em ShareLink
- STL como formato de entrada
- Geração/download de USDZ server-side
