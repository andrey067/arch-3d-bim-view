# Implementation Plan — App 3D Viewer (MVP)

**Feature**: `001-ifc-mvp-platform` (App 3D Viewer MVP)
**Branch**: `main` | **Date**: 2026-06-11
**Spec**: [spec.md](./spec.md) | **Constitution**: v2.0.0 (App 3D Viewer)
**Stack**: Python 3.13+ / FastAPI / Pydantic v2 / SQLAlchemy 2 / Alembic /
PostgreSQL / Redis / Celery / React / TypeScript / Vite / TanStack Query /
React Router / `<model-viewer>` / GLB canônico.

> **Escopo deste plano**: Apenas MVP — autenticação, upload,
> processamento assíncrono, thumbnail, compartilhamento, visualização
> web e AR. Nenhuma feature fora do escopo da Constituição v2.0.0 §12
> é introduzida.
>
> **Não inclui**: código, tarefas, backlog, migrations Alembic, DDL,
> rotas nomeadas finais, screens de UI, ou implementação concreta
> de schemas Pydantic/SQLAlchemy. Esses artefatos pertencem a
> `/speckit-tasks` e à fase de implementação.

---

## 1. Sumário arquitetural

O **App 3D Viewer** é uma plataforma web para profissionais de
arquitetura, design de interiores, marcenaria e modelagem 3D
compartilharem modelos com seus clientes. O fluxo canônico é:
autenticar → fazer upload de um modelo 3D → o sistema converte para
GLB e gera thumbnail em background → o sistema cria um link público
→ o cliente abre o link no navegador → o cliente visualiza o
modelo 3D e, quando o dispositivo suporta, entra em AR.

A solução é um **monorepo** com **uma API FastAPI** servindo o
frontend e expondo endpoints REST/JSON. Processamento de geometria
roda em **worker Celery** (mesmo código Python, imagem Docker
dedicada por causa das dependências de Blender/IfcOpenShell).
Persistência em **PostgreSQL**. Fila e cache em **Redis**.
Armazenamento de arquivos em **disco local** com abstração
`ObjectStorage` para troca futura. Frontend em **React + TypeScript
+ Vite**, organizado por feature, consumindo o backend via
**TanStack Query** e navegando com **React Router**.
Visualização 3D com **`<model-viewer>`**.

O **GLB é o formato interno canônico e único**: todo upload
converge para GLB, e todo o pipeline de visualização/AR consome
GLB. O resultado entregue ao cliente é o GLB + thumbnail WebP.

---

## 2. Arquitetura de alto nível

### 2.1 Visão de containers

```
┌─────────────────────────────────────────────────────────────┐
│  apps/frontend  (SPA React + TS + Vite)                      │
│  servido por nginx como arquivos estáticos                  │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  apps/backend  (FastAPI)                                    │
│   - API HTTP /api/v1/*                                      │
│   - Endpoints públicos de share /s/{token}                  │
│   - Enfileira tarefas de conversão                          │
└──────────┬───────────────────┬────────────────────┬──────────┘
           │                   │                    │
           ▼                   ▼                    ▼
    ┌────────────┐     ┌──────────────┐    ┌──────────────────┐
    │ PostgreSQL │     │  Redis       │    │ storage/         │
    │            │     │  (broker +   │    │   originals/     │
    │            │     │   result)    │    │   converted/     │
    │            │     │              │    │   thumbnails/    │
    └────────────┘     └──────┬───────┘    └────────┬─────────┘
                              │                     │
                              ▼                     │ (acesso a FS)
                       ┌──────────────────┐         │
                       │  Worker Celery   │◄────────┘
                       │  (apps/backend/  │
                       │   app/conversion)│
                       │                  │
                       │  - IfcOpenShell  │
                       │  - Blender       │
                       │  - (apenas        │
                       │   IfcOpenShell +  │
                       │   Blender;        │
                       │   sem Trimesh/     │
                       │   Open3D/          │
                       │   pygltflib)      │
                       └──────────────────┘
```

### 2.2 Decisões de deploy (sem Dockerfiles aqui)

- **API e worker compartilham o mesmo código Python**
  (`apps/backend/`) mas têm entrypoints separados: `uvicorn
  app.main:app` para a API; `celery -A app.conversion.worker
  worker` para o worker.
- **Worker tem imagem Docker dedicada** (`infra/docker/worker/`)
  porque suas dependências (Blender, IfcOpenShell) são pesadas e
  não devem inflar a imagem da API.
- **PostgreSQL e Redis** rodam em containers separados
  (`infra/docker/postgres/`, `infra/docker/redis/`).
- **Storage** é um volume montado em `/storage` no backend e no
  worker (mesma pasta física). Em produção, pode ser um volume
  Docker nomeado; em dev, um bind mount no host.
- **Frontend** é buildado para assets estáticos e servido por
  nginx; nginx também faz proxy reverso para `/api/v1/*` e
  `/s/*` na API.

### 2.3 Layout do monorepo (raiz)

```
.
├── apps/
│   ├── frontend/                  # React + TS + Vite (SPA)
│   └── backend/                   # FastAPI + Celery
│       └── app/
│           ├── core/              # config, db, redis, storage, security
│           ├── features/          # vertical slice
│           │   ├── auth/
│           │   ├── projects/
│           │   ├── models/        # upload + ModelFile
│           │   ├── conversion/    # worker Celery + tasks
│           │   ├── sharing/       # ShareLink
│           │   └── viewer/        # endpoints públicos /s/*
│           └── main.py
├── infra/
│   └── docker/                    # Dockerfiles, compose
├── docs/                          # docs não-específicas-de-feature
├── storage/                       # mount do volume (originals/converted/thumbnails)
├── specs/
│   └── 001-ifc-mvp-platform/      # este plano e artefatos
└── README.md
```

> **Nota sobre `apps/converter/`** (do plano antigo v1.x): o
> conversor agora vive **dentro de `apps/backend/app/conversion/`**
> como módulo de worker. Não há um `apps/converter/` separado; o
> usuário pediu um monorepo com `apps/{frontend,backend}`, e a
> Constituição v2.0.0 não exige um pacote conversor independente.
> Isso simplifica deploy (uma única base de código Python
> com dois entrypoints) e respeita o princípio 1 (simplicidade).

---

## 3. Estrutura dos módulos (Vertical Slice)

### 3.1 Backend — `apps/backend/app/features/`

Cada feature é **autônoma**: contém tudo o que precisa para
funcionar — sem dependências entre features senão via
`core/` (config, db, redis, storage, security).

```
features/
├── auth/
│   ├── router.py            # FastAPI routes (register, login, refresh, logout)
│   ├── schemas.py           # Pydantic v2 request/response
│   ├── service.py           # lógica: hash, JWT, refresh rotation
│   ├── persistence.py       # User repository (queries específicas)
│   ├── models.py            # SQLAlchemy 2 Mapped[User]
│   └── tests/
│       ├── test_auth_service.py
│       └── test_auth_router.py
│
├── projects/
│   ├── router.py            # CRUD de Project
│   ├── schemas.py
│   ├── service.py           # create/list/archive/delete
│   ├── persistence.py
│   ├── models.py            # SQLAlchemy 2 Mapped[Project]
│   └── tests/
│
├── models/                  # feature de upload de ModelFile
│   ├── router.py            # POST /projects/{id}/files (multipart)
│   ├── schemas.py           # ModelFile response (sem metadata no MVP)
│   ├── service.py           # valida magic bytes, calcula hash, enfileira
│   ├── persistence.py
│   ├── models.py            # Mapped[ModelFile], Mapped[ConversionJob]
│   ├── detection.py         # identifica source_format por magic bytes
│   └── tests/
│       ├── test_upload_validation.py
│       └── test_upload_router.py
│
├── conversion/              # worker Celery + tasks
│   ├── worker.py            # Celery app
│   ├── tasks.py             # process_model_file
│   ├── pipelines/
│   │   ├── ifc.py           # IfcOpenShell (extrai geometria/material/UV)
│   │   ├── mesh.py          # Blender headless (DAE/OBJ/GLB → GLB)
│   │   ├── thumbnail.py     # Blender headless → WebP
│   │   └── common.py        # orquestração e normalização (eixos, escala)
│   ├── service.py           # orquestra o pipeline; atualiza job
│   └── tests/
│       ├── test_ifc_pipeline.py
│       ├── test_mesh_pipeline.py
│       └── test_thumbnail.py
│
├── sharing/                 # ShareLink autenticado (owner)
│   ├── router.py            # POST /projects/{id}/shares, revoke
│   ├── schemas.py
│   ├── service.py           # gera token opaco
│   ├── persistence.py
│   ├── models.py            # Mapped[ShareLink]
│   └── tests/
│
└── viewer/                  # endpoints públicos de share
    ├── router.py            # GET /s/{token}, /manifest, /model.glb, /thumbnail.webp
    ├── service.py           # resolve token (revogação bloqueia)
    └── tests/
        └── test_public_share.py
```

**Módulos compartilhados** em `core/`:

```
core/
├── config.py                # Pydantic Settings
├── db.py                    # SQLAlchemy 2 engine + session
├── redis.py                 # Redis client
├── storage/
│   ├── base.py              # Protocol ObjectStorage
│   └── local_disk.py        # LocalDiskStorage
├── security/
│   ├── password.py          # hash/verify
│   ├── jwt.py               # encode/decode access
│   └── refresh.py           # rotação de refresh
├── logging.py               # JSON estruturado + correlation_id
└── errors.py                # mapeamento de exceções → HTTP
```

**Princípios aplicados**:
- **Sem Repository genérico**, sem Unit of Work, sem camadas
  globais. `persistence.py` é apenas um módulo de queries
  específicas da feature.
- **Sem DDD**, sem agregados, sem value objects. SQLAlchemy 2
  `Mapped` e Pydantic v2 são suficientes.
- Cada feature tem seus próprios `tests/`. Testes de integração
  usam `httpx.AsyncClient` + DB de teste.

### 3.2 Frontend — `apps/frontend/src/`

```
src/
├── app/                     # bootstrap (router, providers, query client)
│   ├── router.tsx
│   ├── queryClient.ts
│   └── providers.tsx
├── features/                # feature folders
│   ├── auth/                # login, register, refresh
│   ├── projects/            # list, create, detail, archive
│   ├── upload/              # upload widget, drag-drop, validação client
│   ├── models/              # list ModelFile, ver status do job
│   ├── viewer/              # <model-viewer> wrapper, AR launcher
│   └── sharing/             # criar/listar/revogar share links
├── shared/                  # componentes utilitários
│   ├── api/                 # cliente HTTP + tipos
│   ├── components/          # Button, Card, Spinner, ErrorBoundary
│   ├── hooks/               # useAuth, useProjects, useJobStatus
│   └── types/               # tipos compartilhados
├── pages/                   # roteamento para top-level
│   ├── HomePage.tsx
│   ├── ProjectDetailPage.tsx
│   ├── SharePage.tsx        # /s/:token
│   └── LoginPage.tsx
└── main.tsx
```

**Princípios aplicados**:
- Componentes de feature não importam de outras features; tudo
  compartilhado vai em `shared/`.
- Hooks TanStack Query são coespecíficos à feature
  (`features/projects/useProjects.ts`).
- TypeScript estrito: `strict: true`, `noUncheckedIndexedAccess: true`,
  `noImplicitOverride: true`. Sem `any`, sem `@ts-ignore`.

---

## 4. Fluxos principais

### 4.1 Upload → Processamento → Share

```
┌────────┐  ①POST /api/v1/auth/login     ┌────────────┐
│ Cliente│ ───────────────────────────► │  FastAPI   │
│(owner) │ ◄────────── 200 (JWT) ─────── │  /auth     │
└───┬────┘                               └────────────┘
    │  ②POST /api/v1/projects/{id}/files (multipart)
    ▼
┌────────────┐
│  FastAPI   │
│  /models   │
└────┬───────┘
     │ - valida JWT
     │ - detecta source_format por magic bytes
     │ - calcula content_hash
     │ - persiste ModelFile
     │ - cria ConversionJob(status=pending)
     │ - enfileira Celery task
     │ - responde 202 {model_file_id, conversion_job_id, status: pending}
     ▼
┌────────────┐          ┌─────────────┐
│  Redis     │ ◄──────  │   Celery    │
│  (broker)  │ ────────►│   worker    │
└────────────┘          └──────┬──────┘
                               │ - lê original via ObjectStorage
                               │ - pipeline conforme source_format
                               │   - IFC: IfcOpenShell → Blender headless → GLB
                               │   - DAE/OBJ: Blender headless → GLB
                               │   - GLB: Blender headless normaliza
                               │ - Blender headless render → thumbnail.webp
                               │ - persiste GLB + thumbnail
                               │ - atualiza ConversionJob(ready)
                               ▼
                          ┌────────────┐
                          │  Postgres  │
                          │ (job, paths│
                          │  no DB)    │
                          └────────────┘

┌────────┐  ③GET /api/v1/jobs/{job_id}    ┌────────────┐
│ Cliente│ ───────────────────────────►  │  FastAPI   │
│(owner) │ ◄── 200 {status, glb_url, ...}│  /jobs     │
└───┬────┘                               └────────────┘
    │  ④POST /api/v1/projects/{id}/shares
    ▼
┌────────────┐
│  FastAPI   │
│  /sharing  │ gera token opaco, persist ShareLink
└────┬───────┘
     │
     ▼
  Resposta: {url: "/s/{token}"}
```

### 4.2 Visualização pública (cliente final)

```
┌────────┐  ①GET /s/{token}                ┌────────────┐
│Cliente │ ───────────────────────────►   │  FastAPI   │
│final   │ ◄── HTML da SPA ────────────   │  /viewer   │
└───┬────┘                                └────────────┘
    │  ②GET /s/{token}/manifest
    ▼
┌────────────┐
│  FastAPI   │ resolve token (não expirado/revogado),
│  /viewer   │ retorna glb_url + thumbnail_url
└────┬───────┘
     ▼
  Resposta JSON

┌────────┐  ③GET /s/{token}/thumbnail.webp  ┌────────────┐
│Cliente │ ───────────────────────────►    │  FastAPI   │
│(SPA)   │ ◄──── image/webp ────────────   │  storage/  │
└───┬────┘                                 └────────────┘
    │  ④GET /s/{token}/model.glb
    ▼
┌────────────┐
│  FastAPI   │ range request, model/gltf-binary
│  storage/  │ serve o GLB (sem telemetria no MVP)
└────┬───────┘
     ▼
  Binário do GLB

    │  ⑤ <model-viewer src="/s/{token}/model.glb"
    │          ar ar-modes="webxr scene-viewer quick-look">
    ▼
┌────────────┐
│ <model-   │ orbit/zoom na web; AR nativo no Android (Scene Viewer)
│ viewer>   │ e iOS (Quick Look) quando disponível
└────────────┘
```

### 4.3 Re-upload (reprocessar)

- Re-uploads criam um **novo `ModelFile`** + **novo
  `ConversionJob`** dentro do mesmo `Project`.
- `ShareLink`s antigos continuam apontando para o `ModelFile`
  original (imutável).
- Owner pode criar um novo `ShareLink` apontando para o novo
  `ModelFile` se quiser.

---

## 5. Modelo conceitual de dados

Ver [data-model.md](./data-model.md).

Entidades: `User`, `Project`, `ModelFile`, `ConversionJob`,
`ShareLink`. Cardinalidades principais:

- `User 1—N Project` (um owner)
- `Project 1—N ModelFile` (múltiplas versões ao longo do tempo)
- `ModelFile 1—1 ConversionJob` (relação 1:1 histórica — cada
  arquivo tem um job atual; re-uploads criam novos jobs)
- `Project 1—N ShareLink` (múltiplos links simultâneos)
- `ShareLink N—1 ModelFile` (link aponta para **uma** versão)
- `ShareLink N—1 User` (criador — auditoria)

Estados de `ConversionJob`: `pending → running → {ready | failed}`,
com retry manual via `POST /jobs/{id}/retry` (cria novo job).

---

## 6. Estratégia de processamento

### 6.1 Pipeline por formato

| Formato entrada | Pipeline                                                                 | Bibliotecas                         | Artefatos                |
|---|---|---|---|
| `ifc`  | IfcOpenShell extrai geometria (com materiais/UVs preservados) → Blender headless normaliza e exporta GLB | `ifcopenshell`, `bpy` (Blender) | `model.glb`, `thumbnail.webp` |
| `dae`  | Blender headless importa Collada → exporta GLB (materiais/UVs)            | `bpy` (Blender)                     | `model.glb`, `thumbnail.webp` |
| `obj`  | Blender headless importa Wavefront → exporta GLB                          | `bpy` (Blender)                     | `model.glb`, `thumbnail.webp` |
| `glb`  | Blender headless normaliza (eixos, escala) e gera thumbnail; GLB é o próprio canônico | `bpy` (Blender)                     | `model.glb`, `thumbnail.webp` |

> **Fora do MVP** (sem pipeline; rejeitados com HTTP 415 e
> mensagem clara):
> - `stl` — mesh pura, sem materiais/texturas; **não atende o
>   objetivo do produto** (arquitetura, interiores, móveis
>   planejados). Trimesh ficaria fora sem STL.
> - `rvt`, `dwg`, `dxf` — sem conversor open-source confiável.
> - `skp` — sem licença livre do formato.
>
> **Bibliotecas explicitamente fora do MVP**: `Trimesh`,
> `Open3D`, `pygltflib`. Reintroduzir **apenas** quando aparecer
> FR concreto (decimação, simplificação, LOD, mesh repair,
> inspeção programática de GLB).

### 6.2 Thumbnail

- Gerado por **Blender headless** com câmera automática
  enquadrando o bounding box.
- Saída: `thumbnail.webp` (preferência por WebP por tamanho).
- Tamanho: configurável (default 800×600).
- Render é parte do mesmo pipeline do worker; não é job separado.

### 6.3 Prioridades de preservação (Constituição §4)

Em todos os pipelines, a ordem de prioridade é:
1. materiais
2. texturas
3. UV mapping
4. metadados BIM (best-effort, descartáveis)

Concretamente:
- IFC: IfcOpenShell extrai geometria **com mapeamento de materiais**
  por `IfcSurfaceStyle`; texturas e UVs são preservadas via
  embedded textures. O GLB é então produzido por Blender headless
  (importação da malha intermediária + export GLB canônico). Se
  houver perda de material semântico, a geometria é preservada com
  cor básica.
- DAE/OBJ via Blender: importação nativa preserva materiais/UVs;
  exporta GLB com `KHR_materials_unlit` quando aplicável, e
  embedded textures.
- GLB: Blender normaliza (eixos, escala) e gera thumbnail; o GLB é
  o próprio artefato canônico.

### 6.4 Idempotência e retry

- Worker lê `ConversionJob` e faz update condicional
  (`WHERE status='pending' OR (status='failed' AND attempts <
  MAX_ATTEMPTS)`) antes de mutar.
- Em `failed`, o `last_error` é persistido para diagnóstico.
- Retry manual (`POST /jobs/{id}/retry`) cria novo job; re-uploads
  criam novo `ModelFile` + novo job.
- `attempts` é contador por job, não global.

### 6.5 Limites e timeouts

- `MAX_UPLOAD_MB` — limite de upload.
- `MAX_CONVERSION_TIMEOUT_S` — timeout duro por job.
- `MAX_CONVERSION_ATTEMPTS` — tentativas automáticas.

Valores numéricos finais são responsabilidade da implementação
dentro dos limites do MVP.

---

## 7. Estratégia de armazenamento

### 7.1 Abstração `ObjectStorage`

Definida em `core/storage/base.py` como `Protocol`:

```python
class ObjectStorage(Protocol):
    def put(self, key: str, src: Path | BinaryIO, content_type: str) -> str: ...
    def get(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def get_size(self, key: str) -> int: ...
    def open_for_read(self, key: str) -> BinaryIO: ...  # streaming
```

A primeira implementação é `LocalDiskStorage` em
`core/storage/local_disk.py`. Trocar para S3/MinIO no futuro
significa **adicionar** uma nova implementação e configurar a
injeção de dependência — sem alterar call sites.

### 7.2 Layout físico

```
storage/
├── originals/
│   └── <project_id>/
│       └── <model_file_id>__<sanitized_filename>
├── converted/
│   └── <project_id>/
│       └── <model_file_id>.glb
└── thumbnails/
    └── <project_id>/
        └── <model_file_id>.webp
```

- Isolamento por `project_id` permite remoção atômica via
  `rm -rf storage/*/<project_id>/`.
- `model_file_id` no path torna o storage seguro contra colisão
  de nomes de arquivo.

### 7.3 Chaves (`storage_key`)

- Persistidas no banco (`ModelFile.original_storage_key`,
  `ConversionJob.glb_storage_key`, `ConversionJob.thumbnail_storage_key`).
- Sempre **paths relativos** à raiz `storage/`; nunca absolutos.
- Content-Type armazenado no banco (`ModelFile.content_type`) e
  usado pelo `viewer/` ao servir o asset.

### 7.4 Serving de assets

- **Privado** (autenticado por JWT): se houver endpoint de download
  autenticado (futuro, fora do MVP).
- **Público via share**: `/s/{token}/model.glb`,
  `/s/{token}/thumbnail.webp` — autenticação pela posse do token.
- Suporte a **HTTP Range requests** para o GLB (essencial para
  `<model-viewer>` em conexões lentas).
- `Content-Type` correto: `model/gltf-binary`, `image/webp`.

### 7.5 Migração futura (fora do MVP)

Quando o tráfego justificar object storage:
1. Adicionar `S3Storage(ObjectStorage)` em `core/storage/`.
2. Configurar `STORAGE_BACKEND=s3` em `Settings`.
3. Migrar dados com um job único de cópia (origem: disco; destino:
   bucket) — sem mudança de schema, pois o banco guarda apenas
   `storage_key` (string).
4. Servir assets diretamente via URL pré-assinada (futuro).

---

## 8. Estratégia de autenticação

### 8.1 JWT Access Token

- Algoritmo: `HS256` (chave simétrica em env) ou `RS256`
  (chave assimétrica) — `HS256` no MVP por simplicidade.
- Payload: `{ "sub": "user_id", "exp": ..., "iat": ... }`.
- TTL: 15 minutos (constante em `core/security/jwt.py`).
- Validação em **dependency FastAPI** `get_current_user`.

### 8.2 Refresh Token

- Token opaco (32 bytes hex), gerado por `secrets.token_hex(32)`.
- Armazenado no banco como **hash** (SHA-256), nunca em texto puro.
- TTL: 30 dias, com **rotação obrigatória** a cada uso (o
  presented token é invalidado e um novo é emitido).
- Detecção de reuso de token revogado → revoga **toda a família**
  do token (proteção contra roubo).

### 8.3 Senha

- Hashing com `bcrypt` (passlib) ou `argon2id`.
- Validação: ≥ 8 chars, email-like é rejeitado.
- Nunca exposto em responses ou logs.

### 8.4 Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

Ver [contracts/openapi.md](./contracts/openapi.md).

---

## 9. Camadas compartilhadas (`core/`)

Decisões de design para evitar god-folders e manter vertical
slice:

- `core/config.py` — Pydantic Settings, lê env vars.
- `core/db.py` — engine SQLAlchemy 2, `SessionLocal`, dependency
  `get_db`.
- `core/redis.py` — Redis client, dependency `get_redis`.
- `core/storage/` — abstração `ObjectStorage` + `LocalDiskStorage`.
- `core/security/` — hash de senha, JWT, rotação de refresh.
- `core/logging.py` — JSON estruturado, `correlation_id` propagado.
- `core/errors.py` — mapeamento de exceções → HTTP.

Nenhum desses módulos importa de `features/*`. Features podem
importar de `core/*`.

---

## 10. Estratégia de testes (Constituição §9)

- **Unit**: cobertura por feature, especialmente em `service.py`
  e `pipelines/`. Sem rede, sem DB, sem filesystem (exceto
  fixtures controladas).
- **Integração**: `httpx.AsyncClient` + TestClient do FastAPI +
  DB de teste (SQLite in-memory não serve para JSONB/UUID; usar
  Postgres em container efêmero ou schema separado por teste).
- **Worker**: `CELERY_TASK_ALWAYS_EAGER=True` em tests, ou
  Redis em container efêmero.
- **Frontend**: `vitest` + `@testing-library/react` para hooks
  e componentes; `playwright` E2E é deferido (fora do MVP).
- **Cobertura mínima**: a definir por feature, com gate
  qualitativo ("nenhuma feature sem testes" — Constituição §9).

---

## 11. Observabilidade mínima (Constituição §19 de research)

- Logs JSON em stdout (capturados por Docker).
- Campos: `timestamp`, `level`, `correlation_id`, `user_id`,
  `project_id`, `model_file_id`, `job_id`, `route`, `method`,
  `status`, `duration_ms`, `error`.
- Sem APM/metrics server no MVP.

---

## 12. Stack de execução (resumo)

| Camada | Tecnologia | Justificativa |
|---|---|---|
| API HTTP | FastAPI 0.115+ | Async, OpenAPI auto, Pydantic v2 |
| Validação | Pydantic v2 | Tipos, schemas, validação de borda |
| ORM | SQLAlchemy 2 (`Mapped`) | Type hints modernos, migrations com Alembic |
| Migrations | Alembic | Padrão de fato para SQLAlchemy |
| Banco | PostgreSQL 16 | JSONB, UUID, transações ACID |
| Fila | Celery 5 | Padrão Python, retry/backoff |
| Broker | Redis 7 | Latência baixa, simplicidade |
| Storage | Disco local + Protocol | Abstração permite migração futura |
| Frontend build | Vite 5 | HMR rápido, build enxuto |
| Frontend framework | React 18+ + TS estrito | Stack oficial |
| Data fetching | TanStack Query 5 | Cache/retry/refetch prontos |
| Roteamento | React Router 6 | Padrão de fato |
| Viewer | `<model-viewer>` 3+ | AR nativo, controles prontos |
| Auth | JWT próprio + bcrypt/argon2 | Sem dependência externa |
| Conversão | IfcOpenShell + Blender Headless | Trimesh/Open3D/pygltflib explicitamente fora do MVP |
| Testes backend | pytest + httpx + pytest-asyncio | Padrão FastAPI |
| Testes frontend | vitest + @testing-library/react | Padrão Vite/React |
| Container | Docker + Compose | Reprodutibilidade |

---

## 13. Constitution Check (pós-design)

| Princípio | Status | Evidência |
|---|---|---|
| 1. Simplicidade | ✅ Pass | Stack homogênea; sem Repository genérico, sem DDD/CQRS/Mediator, sem camadas especulativas. |
| 2. Vertical Slice | ✅ Pass | `features/<name>/{router,schemas,service,persistence,models,tests}`. |
| 3. Backend Python | ✅ Pass | FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + Postgres + tipagem total. |
| 4. Conversão de Arquivos | ✅ Pass | IfcOpenShell + Blender Headless; Trimesh/Open3D/pygltflib explicitamente fora do MVP (reintroduzir só com FR concreto); materiais/texturas/UVs > BIM. |
| 5. Frontend | ✅ Pass | React + TS estrito + Vite + TanStack Query + React Router. |
| 6. Visualização | ✅ Pass | GLB canônico; `<model-viewer>` primário, Three.js disponível. |
| 7. Armazenamento | ✅ Pass | Disco local + `ObjectStorage` Protocol; sem MinIO/S3 no MVP. |
| 8. Processamento Assíncrono | ✅ Pass | Celery + Redis; HTTP nunca bloqueia. |
| 9. Testabilidade | ✅ Pass | Toda feature com unit + integração; pytest + vitest. |
| 10. Proibição de Assunções | ✅ Pass | USDZ/AR iOS, viewer avançado, métricas, RVT/DWG/SKP/STL, `view_count`, `metadata`, `expires_at` deferidos explicitamente. |
| 11. Critério de Conclusão | ✅ Pass | Plano não cria tarefas nem código; produção de tarefas e implementação ficam para `/speckit-tasks` e implementação. |
| 12. MVP | ✅ Pass | Lista fechada: upload, processamento, thumbnail, share, view, AR. Tudo presente; nada além. |

**Complexity Tracking**: nenhuma violação identificada.

---

## 14. Migration notes (do v1.x para v2.x)

A Constituição v2.0.0 declara uma migração completa de
ASP.NET Core para Python/FastAPI. Este plano:

1. **Não reescreve código automaticamente.** A migração é
   trabalho separado, com fases explícitas (a serem
   detalhadas em `/speckit-tasks`).
2. **Substitui o layout `app/{backend,converter,frontend,tests}/`**
   pelo layout de monorepo `apps/{frontend,backend}/` +
   `infra/docker/` + `docs/` + `storage/`. A pasta `app/` é
   deprecada.
3. **Substitui ASP.NET Core por FastAPI** com mesma superfície
   REST/JSON (mas com auth JWT próprio).
4. **Substitui sidecar conversor** (`app/converter/`) por
   **worker Celery** dentro de `apps/backend/app/conversion/`.
5. **Mantém GLB como formato canônico** (alinhado com a v1.x).
6. **Remove conversor USDZ** como artefato de worker (o GLB
   basta para a web; AR iOS via Quick Look é uma extensão
   de share/viewer a ser decidida em tasks, **não** no
   plano).

A reescrita do código atual (`app/backend/`, `app/converter/`,
`app/frontend/`) é responsabilidade de uma fase de implementação
dedicada, **não** deste plano. O plano descreve o **alvo**.

---

## 15. Estrutura de artefatos da feature

```
specs/001-ifc-mvp-platform/
├── plan.md              # este arquivo
├── spec.md              # visão de produto
├── research.md          # decisões técnicas (R-1…R-21)
├── data-model.md        # modelo conceitual
├── contracts/
│   └── openapi.md       # API HTTP + payload Celery
├── quickstart.md        # validação E2E
└── (tasks.md a ser gerado por /speckit-tasks)
```

---

## 16. Done When

- [x] Constituição v2.0.0 referenciada.
- [x] Stack congelada respeitada (sem adições).
- [x] Arquitetura de alto nível entregue.
- [x] Estrutura dos módulos (vertical slice) entregue.
- [x] Fluxos principais documentados.
- [x] Modelo conceitual de dados entregue.
- [x] Estratégia de processamento entregue.
- [x] Estratégia de armazenamento entregue.
- [x] Contratos HTTP entregues.
- [x] Constitution Check pós-design preenchido.
- [x] Sem código, sem migrations, sem tarefas (delegado a
  `/speckit-tasks` e à fase de implementação).

---

## 17. Revisões e deltas

### 2026-06-11 — Revisão de simplificação (rejeição parcial)

Itens **removidos** do MVP após análise de simplificação
(rejeitadas as alternativas que violariam a stack/Constitution):

- ❌ **Open3D** — sem FR de decimação/simplificação.
- ❌ **pygltflib** — Blender já produz GLB válido.
- ❌ **Trimesh** — Blender + IfcOpenShell cobrem o pipeline.
  Reintroduzir com FR concreto de mesh repair/LOD.
- ❌ **STL** — mesh pura sem materiais; vai contra o objetivo
  do produto (arquitetura, interiores, móveis planejados).
- ❌ **`ShareLink.view_count`** — telemetria, não-MVP.
- ❌ **`ModelFile.metadata` (vertex/material count etc.)** —
  não há User Story que o exija.
- ❌ **`ShareLink.expires_at`** — share link não expira no MVP.

Itens **mantidos** (discordância do usuário em relação à
análise de simplificação):

- ✅ **TanStack Query** — cache, loading, retry, invalidação
  valem o custo. Ganho de removê-lo é mínimo.
- ✅ **React Router** — 5 rotas (`/`, `/login`, `/dashboard`,
  `/projects/:id`, `/s/:token`) justificam a abstração.
- ✅ **PostgreSQL** — arquivos pesados + fila + workers exigem
  banco de produção desde o MVP.
- ✅ **Celery + Redis** — conversão IFC pode levar 10–60s;
  bloquear a request HTTP é inaceitável.

Formato de entrada suportado no MVP: **`ifc`, `dae`, `obj`, `glb`**.

Formato de entrada rejeitado (HTTP 415): **`stl`, `rvt`, `dwg`,
`dxf`, `skp`**.
