# Quickstart — App 3D Viewer (MVP)

**Feature**: `001-ifc-mvp-platform` (App 3D Viewer MVP)
**Status**: Guia de validação end-to-end. Cobre o MVP completo —
autenticação, upload, conversão assíncrona, thumbnail,
compartilhamento, visualização web e AR.

> Este quickstart descreve **como validar** o sistema rodando
> ponta-a-ponta, sem entrar em implementação de código. Cada
> cenário lista pré-requisitos, comandos (quando aplicável),
> e o resultado esperado. Detalhes de endpoints e contratos
> estão em [contracts/openapi.md](./contracts/openapi.md).

---

## 0. Pré-requisitos

### 0.1 Infraestrutura

- Docker Engine 24+ e Docker Compose v2.
- 8 GB RAM livre (Blender headless + IfcOpenShell exigem).
- Portas locais liberadas: 5432 (Postgres), 6379 (Redis), 8000
  (API), 5173 (frontend dev) ou 8080 (nginx prod).

### 0.2 Conta de serviço

- Subir a stack: `docker compose up -d`.
- A API deve estar respondendo em `http://localhost:8000/api/v1/health`
  com `{"status": "ok"}`.

### 0.3 Cliente de teste

- Navegador moderno (Chrome/Safari/Firefox atual) em desktop.
- Smartphone Android (Chrome + ARCore) — opcional para teste de AR.
- iPhone (Safari) — opcional para teste de AR.

### 0.4 Arquivos de modelo de teste

Prepare ao menos:
- 1 IFC pequeno (≤ 5 MB) — qualquer projeto público com licença
  permissiva serve.
- 1 DAE exportado do SketchUp (ou similar).
- 1 OBJ com texturas referenciadas.
- 1 GLB válido (caso GLB-entrada).

> Atenção: o MVP rejeita STL, SKP, RVT, DWG, DXF com HTTP 415 e
> mensagem clara. Use-os apenas para validar a rejeição.
> STL é mesh pura sem materiais — não atende o objetivo do
> produto (arquitetura, interiores, móveis planejados).

---

## 1. Cenário 1 — Autenticação

**Objetivo**: validar registro, login, refresh e logout com JWT
próprio.

### 1.1 Registrar conta

**Comando** (curl):
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"correct-horse-battery","display_name":"Owner"}'
```

**Esperado**:
- HTTP `201 Created`.
- Response com `id`, `email`, `display_name`, `created_at`.
- Sem `password_hash` no payload.

### 1.2 Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"correct-horse-battery"}'
```

**Esperado**:
- HTTP `200 OK`.
- `access_token` (JWT) e `refresh_token` (opaco).
- `token_type: "Bearer"`, `expires_in: 900`.

### 1.3 Refresh

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-from-1.2>"}'
```

**Esperado**:
- HTTP `200`.
- Novo `access_token` + novo `refresh_token` (rotação).
- O `refresh_token` antigo é invalidado.

### 1.4 Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-from-1.3>"}'
```

**Esperado**: HTTP `204`. Subsequente `refresh` com esse token
retorna `401`.

### 1.5 Edge cases a validar

- Senha fraca (< 8 chars) → `400`.
- Email duplicado no `register` → `409`.
- `refresh` com token revogado → `401`.
- 11 logins errados em 1 minuto → `429` (rate limit).

---

## 2. Cenário 2 — Projeto + Upload IFC

**Objetivo**: criar projeto, fazer upload de IFC, observar
conversão assíncrona, ver artefatos prontos.

### 2.1 Criar projeto

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Casa Cliente A","description":"Reforma sala"}'
```

**Esperado**: HTTP `201`, payload do projeto com `id`.

### 2.2 Upload IFC

```bash
curl -X POST http://localhost:8000/api/v1/projects/<project_id>/files \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/casa.ifc"
```

**Esperado**:
- HTTP `202 Accepted`.
- `model_file_id`, `conversion_job_id`, `status: "pending"`.

### 2.3 Polling de status

```bash
curl http://localhost:8000/api/v1/jobs/<conversion_job_id> \
  -H "Authorization: Bearer <access_token>"
```

**Esperado**:
- Inicialmente: `status: "pending"` ou `running`.
- Após ≤ 5 min: `status: "ready"`, com `glb_url` e
  `thumbnail_url` populados.
- Em caso de falha: `status: "failed"`, `last_error` populado.

### 2.4 Edge cases a validar

- Upload de arquivo > `MAX_UPLOAD_MB` → `413`.
- Upload de `.stl`, `.skp`, `.rvt`, `.dwg`, `.dxf` → `415` com
  mensagem clara de que o formato **não é suportado no MVP**.
- Upload de arquivo com magic bytes inválido (renomear `.exe`
  para `.ifc`) → `415`.

---

## 3. Cenário 3 — DAE/OBJ/GLB

**Objetivo**: validar pipelines alternativos.

Repetir a Seção 2 substituindo o arquivo de entrada por:

### 3.1 DAE (do SketchUp)
- Esperado: conversão via Blender headless → GLB com
  materiais/UVs preservados; thumbnail WebP renderizado.

### 3.2 OBJ
- Esperado: idem 3.1.

### 3.3 GLB (já no formato)
- Esperado: pipeline curto — Blender headless normaliza (eixos,
  escala) e gera thumbnail; o GLB é o próprio canônico.

---

## 4. Cenário 4 — Compartilhamento

**Objetivo**: criar link público, acessar sem autenticação,
reivindicar revogação.

### 4.1 Criar share link

```bash
curl -X POST http://localhost:8000/api/v1/projects/<project_id>/shares \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"model_file_id":"<file_id>"}'
```

**Esperado**: HTTP `201` com `url: "/s/<token>"`.

### 4.2 Acessar página pública

Abrir `http://localhost:8000/s/<token>` no navegador (sem
autenticação).

**Esperado**:
- HTML da SPA renderiza.
- Thumbnail WebP carrega como poster.
- `<model-viewer>` carrega o GLB.
- Controles de orbit, zoom, fullscreen, auto-rotate funcionam.

### 4.3 Inspecionar manifest

```bash
curl http://localhost:8000/s/<token>/manifest
```

**Esperado**: JSON com `glb_url`, `thumbnail_url`, `project_name`,
`uploader_display_name`. (Sem campo `metadata` no MVP — analytics
de geometria é expansão futura.)

### 4.4 Validar assets binários

```bash
curl -I http://localhost:8000/s/<token>/model.glb
curl -I http://localhost:8000/s/<token>/thumbnail.webp
```

**Esperado**:
- `model.glb` → `Content-Type: model/gltf-binary`, `Accept-Ranges: bytes`.
- `thumbnail.webp` → `Content-Type: image/webp`.

### 4.5 Revogar share link

```bash
curl -X POST http://localhost:8000/api/v1/shares/<token>/revoke \
  -H "Authorization: Bearer <access_token>"
```

**Esperado**: HTTP `204`. Subsequente `GET /s/<token>/manifest`
retorna `404` ou `410`.

---

## 5. Cenário 5 — Realidade Aumentada

**Objetivo**: validar AR Android (Scene Viewer) e iOS (Quick Look).

### 5.1 AR Android (Scene Viewer)

Pré-requisito: dispositivo Android com ARCore + Google Play
Services for AR instalado.

1. Abrir `https://<host>/s/<token>` no Chrome Android.
2. Tocar no botão AR (badge nativo do `<model-viewer>`).
3. Posicionar o modelo no plano detectado.
4. Tirar foto da cena com o modelo sobreposto.

**Esperado**:
- Cena renderiza com materiais e texturas do GLB.
- Escala coerente com o `meters` declarado no GLB.

### 5.2 AR iOS (Quick Look)

Pré-requisito: iPhone com iOS 13+ e Safari.

> **Nota MVP**: a geração de USDZ para Quick Look a partir do
> GLB é uma extensão de share/viewer. No MVP, a abordagem
> mais simples é o `<model-viewer>` consumir o GLB diretamente
> e gerar um USDZ on-the-fly ou delegar a um serviço dedicado
> em uma fase de tasks dedicada. Este quickstart registra o
> **resultado esperado** (Quick Look funciona), mas a
> implementação concreta de USDZ pode variar e é deferida
> para tasks.

1. Abrir a URL pública do share no Safari iOS.
2. Tocar no botão AR.
3. **Cenário A** (com USDZ): Quick Look nativo abre; o modelo
   é renderizado em AR.
4. **Cenário B** (sem USDZ no MVP): o `<model-viewer>` mostra
   um fallback "AR não disponível" no iOS — isso é aceitável
   para o MVP inicial; o refinamento é responsabilidade de
   tasks futuras.

**Esperado (mínimo MVP)**: web viewer funciona em iOS Safari.
**Esperado (target)**: AR iOS via Quick Look.

### 5.3 Edge cases a validar

- GLB sem `meters` definido → a escala pode parecer errada em
  AR; documentar como limitação.
- Modelo com muitos triângulos (> 1M) → pode falhar em
  dispositivos modestos; documentar.
- HTTPS obrigatório para AR — em localhost o AR não vai
  funcionar; testar via tunnel (ngrok, Caddy) ou deploy em
  staging com TLS válido.

---

## 6. Cenário 6 — Re-upload e Reprocessamento

**Objetivo**: validar que re-uploads criam novos ModelFiles e
novos Jobs, sem perder o histórico.

1. No mesmo projeto, fazer upload de uma nova versão do mesmo
   modelo (ex.: `casa-v2.ifc`).
2. Verificar que existe um novo `ModelFile` (com novo `id`).
3. Verificar que existe um novo `ConversionJob` (com novo `id`).
4. `GET /projects/<id>` → lista contém ambos os `ModelFile`s.
5. `ShareLink`s antigos continuam apontando para `ModelFile` v1.
6. Criar novo `ShareLink` apontando para v2.

**Esperado**:
- Histórico preservado.
- Links antigos continuam funcionando.
- Cada versão tem seu próprio GLB e thumbnail.

---

## 7. Cenário 7 — Edge cases transversais

### 7.1 Autenticação

- Acessar `/api/v1/projects` sem token → `401`.
- Token expirado (esperar 15 min) → `401` com mensagem de
  expiração.

### 7.2 Permissões

- Owner A cria projeto; Owner B tenta `GET /projects/<id>` do A
  → `404` (não revela existência).

### 7.3 Resiliência

- Worker Celery derrubado durante conversão → `GET /jobs/<id>`
  mostra `pending` indefinidamente; ao subir o worker, o job
  entra em `running` (Celery retoma).
- Disco cheio durante conversão → `failed` com `last_error`
  contendo mensagem do sistema operacional.

### 7.4 Rate limit

- 11 uploads em 1 minuto → `429` no 11º.

---

## 8. Critérios de aceitação resumidos (MVP)

| ID | Critério | Cenário |
|---|---|---|
| AC-1 | Usuário pode se registrar, logar, refresh, logout. | 1 |
| AC-2 | Owner pode criar projeto. | 2.1 |
| AC-3 | Upload de IFC retorna 202 com job ID. | 2.2 |
| AC-4 | Job transita `pending → running → ready`. | 2.3 |
| AC-5 | GLB e thumbnail WebP são persistidos em `storage/`. | 2.3 |
| AC-6 | Upload rejeita STL/SKP/RVT/DWG/DXF com `415`. | 2.4 |
| AC-7 | DAE/OBJ/GLB são convertidos via pipelines correspondentes. | 3 |
| AC-8 | Share link é gerado e acessível sem auth. | 4.1, 4.2 |
| AC-9 | Endpoint público serve GLB com `Content-Type` e `Range` corretos. | 4.4 |
| AC-10 | Revogação invalida o share link. | 4.5 |
| AC-11 | AR Android (Scene Viewer) renderiza o modelo. | 5.1 |
| AC-12 | Web viewer mostra orbit, zoom, fullscreen, poster, auto-rotate. | 4.2 |
| AC-13 | Re-uploads não sobrescrevem versões anteriores. | 6 |
| AC-14 | Endpoints autenticados exigem JWT válido. | 7.1 |
| AC-15 | Endpoints respeitam ownership (cross-owner → 404). | 7.2 |

---

## 9. Critérios de não-aceitação (fora do MVP)

Os itens abaixo **não** devem ser assumidos como entregues e
sua ausência **não é regressão**:

- Comentários em modelos.
- Versionamento semântico explícito (v1, v2, v3...).
- Permissões granulares (roles, ACL).
- Digital twin / telemetria de visualização.
- Métricas operacionais expostas (Prometheus, etc.).
- API admin.
- BIM tree, propriedades IFC, medições, classificação.
- STL como formato de entrada (mesh pura, sem materiais).
- Migração para object storage (S3/MinIO).
- Geração automática de USDZ on-the-fly (target, mas
  implementação concreta é decisão de tasks).
- OpenTelemetry/APM tracing.
- Multi-tenant.
- `view_count` e `metadata` extraído do modelo (analytics).
- `expires_at` em ShareLink (expiração automática).

---

## 10. Como executar localmente (referência)

> Os comandos abaixo são **referência** de como a stack será
> operada. Nenhum script de bootstrap é introduzido por este
> plano.

```bash
# Subir stack
docker compose up -d

# Verificar health
curl http://localhost:8000/api/v1/health

# Rodar migrations (após implementação)
docker compose exec backend alembic upgrade head

# Acompanhar worker
docker compose logs -f worker

# Abrir frontend
open http://localhost:5173   # dev (Vite)
# ou
open http://localhost:8080   # prod (nginx)
```

---

## 11. Done When

- [x] Todos os cenários do MVP listados com pré-requisitos,
  comandos, e resultados esperados.
- [x] Edge cases transversais (auth, permissão, resiliência,
  rate limit) cobertos.
- [x] Critérios de aceitação mapeados.
- [x] Fora-do-MVP declarado explicitamente.
