# Tasks: App 3D Viewer — MVP (Vertical Slice)

**Input**: Design documents from `specs/001-ifc-mvp-platform/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/openapi.md`, `quickstart.md`
**Constitution**: v2.0.0 — App 3D Viewer
**Branch**: `001-ifc-mvp-platform` (legacy directory name; rename deferred)
**Updated**: 2026-06-11

> **Organização**: Tarefas organizadas por **Vertical Slice** (fluxo de
> negócio end-to-end), **NÃO** por camada técnica. Não há épicos de
> Models / Repositories / Services / Controllers. Cada fase entrega
> um incremento testável de forma independente, do input do usuário
> até o output do sistema.

> **Stack congelada** (Constituição v2.0.0 §3–§5): Backend
> Python 3.13+/FastAPI/Pydantic v2/SQLAlchemy 2/Alembic/PostgreSQL;
> Frontend React 18+/TypeScript strict/Vite/TanStack Query/React
> Router; Viewer `<model-viewer>` 3+; Conversão Blender Headless +
> IfcOpenShell; Celery + Redis; Local Disk + `ObjectStorage` Protocol.
> Trimesh/Open3D/pygltflib **fora** do MVP. STL/RVT/DWG/DXF/SKP
> **rejeitados** com HTTP 415.

> **Sem `view_count`/`metadata`/`expires_at` no MVP** (R-17, R-18).

---

## Formato das Tarefas

`- [ ] [ID] [P?] [VS?] Descrição`

- **[P]**: Executável em paralelo (arquivos distintos, sem dependências incompletas)
- **[VS]**: Vertical Slice da fase (`[VS-InfraBE]`, `[VS-Auth]`, etc.)
- **Campos por tarefa**: objetivo, dependências, critérios de aceite (ver bloco de cada task)
- **Não gerar código** neste documento — apenas a especificação executável

---

## Sumário por Vertical Slice

| # | Vertical Slice | Fase | Tarefas | Status |
|---|---|---|---|---|
| 1 | Infraestrutura Backend | Fundação | T001–T008 | ✅ Concluído |
| 2 | Infraestrutura Frontend | Fundação | T009–T014 | ✅ Concluído |
| 3 | Autenticação | Fluxo de Negócio | T015–T021 | ✅ Concluído |
| 4 | Upload | Fluxo de Negócio | T022–T027 | ✅ Concluído |
| 5 | Storage | Fluxo de Negócio | T028–T031 | ✅ Concluído |
| 6 | Conversão | Fluxo de Negócio | T032–T038 | ✅ Concluído |
| 7 | Thumbnail | Fluxo de Negócio | T039–T042 | ✅ Concluído |
| 8 | Viewer | Fluxo de Negócio | T043–T048 | ✅ Concluído |
| 9 | Compartilhamento | Fluxo de Negócio | T049–T053 | ✅ Concluído |
| 10 | Visualização Pública | Fluxo de Negócio | T054–T058 | ✅ Concluído |
| 11 | AR | Fluxo de Negócio | T059–T062 | ✅ Concluído |
| 12 | Testes | Cross-cutting | T063–T067 | ✅ Concluído |
| 13 | Docker | Cross-cutting | T068–T072 | ✅ Concluído |

**Total**: 72 tarefas

---

## Phase 1: Infraestrutura Backend ✅

**Objetivo**: Estabelecer a fundação do backend Python/FastAPI — base de código, dependências, configuração, banco, migrations, observabilidade, contrato OpenAPI inicial e entrypoints separados (API e worker) — **sem features de negócio**.

**Independência**: Esta fase é **pré-requisito bloqueante** para todas as demais. Não há feature de negócio sem essa base.

**Independente Test**: `docker compose up backend` → `GET /api/v1/health` retorna `200 {"status":"ok"}`; `GET /api/v1/health/ready` retorna `200` quando DB e Redis respondem; `alembic upgrade head` aplica migrations sem erro; `celery -A app.conversion.worker worker` sobe e responde a `ping`.

**Status**: ✅ Concluído — todos os testes passam, ruff limpo, mypy ok.

### T001 — Bootstrap do monorepo `apps/backend/` (Python 3.13+ / FastAPI) ✅

- **Objetivo**: Inicializar o pacote Python `apps/backend/` com `pyproject.toml` (Poetry/uv), `app/` com entrypoint único (`main.py`) e estrutura-alvo `features/<name>/` vazia.
- **Dependências**: nenhuma
- **Critérios de aceite**:
  - `apps/backend/pyproject.toml` declara Python `>=3.13`, FastAPI 0.115+, Pydantic v2, SQLAlchemy 2, Alembic
  - `apps/backend/app/main.py` cria `FastAPI()` mínimo, monta routers vazios, expõe `/api/v1/health`
  - `apps/backend/app/features/__init__.py` existe; subdiretórios de features virão nas fases seguintes
  - `uvicorn app.main:app --reload` sobe sem warning
  - `mypy --strict` passa em `app/main.py`

### T002 — `core/config.py` (Pydantic Settings) e carregamento de env ✅

- **Objetivo**: Centralizar todas as configurações em `Pydantic Settings` (env-driven) — `DATABASE_URL`, `REDIS_URL`, `STORAGE_BACKEND=local`, `STORAGE_ROOT`, `JWT_SECRET`, `JWT_ALG=HS256`, `ACCESS_TOKEN_TTL_S=900`, `REFRESH_TOKEN_TTL_D=30`, `MAX_UPLOAD_MB`, `MAX_CONVERSION_TIMEOUT_S`, `MAX_CONVERSION_ATTEMPTS`, `CORS_ORIGINS`.
- **Dependências**: T001
- **Critérios de aceite**:
  - `Settings(BaseSettings)` em `app/core/config.py` lê de env e arquivo `.env`
  - Falta de `JWT_SECRET` em produção aborta startup com erro claro
  - `get_settings()` retorna singleton cacheado
  - Teste unitário valida defaults e override via env

### T003 — `core/db.py` (SQLAlchemy 2 engine, `SessionLocal`, `get_db`) ✅

- **Objetivo**: Engine síncrona (worker Celery é síncrono) e `SessionLocal`; dependency `get_db` que fecha sessão após request.
- **Dependências**: T002
- **Critérios de aceite**:
  - Engine criado a partir de `Settings.DATABASE_URL` com `pool_pre_ping=True`
  - `get_db()` é generator FastAPI
  - Teste de integração: `SELECT 1` retorna 1 via `SessionLocal`
  - `Mapped[T]` typing aplicado nas futuras models (validado em T004+)

### T004 — `core/redis.py` (Redis client + `get_redis`) ✅

- **Objetivo**: Cliente Redis singleton e dependency; usado por Celery (broker) e por rate-limiting futuro.
- **Dependências**: T002
- **Critérios de aceite**:
  - `redis.Redis.from_url(Settings.REDIS_URL, decode_responses=True)` instanciado lazy
  - `get_redis()` é dependency FastAPI
  - Teste unitário: PING retorna `True`

### T005 — Migrations Alembic (init + primeira migration `users/projects/model_files/conversion_jobs/share_links`) ✅

- **Objetivo**: Inicializar Alembic em `apps/backend/alembic/`, gerar migration inicial refletindo **todas as 5 entidades** do `data-model.md` (User, Project, ModelFile, ConversionJob, ShareLink) com UUIDs PKs, FKs e índices necessários.
- **Dependências**: T003
- **Critérios de aceite**:
  - `alembic init` dentro de `apps/backend/`
  - `alembic.ini` lê `sqlalchemy.url` de `Settings.DATABASE_URL` via `env.py`
  - Migration `0001_initial.py` cria as 5 tabelas com constraints conforme `data-model.md`
  - `alembic upgrade head` em DB PostgreSQL vazio aplica sem erro
  - `alembic downgrade base` reverte sem erro
  - **Não inclui** colunas `view_count`, `metadata`, `expires_at` (R-17, R-18)

### T006 — `core/logging.py` (JSON estruturado + `correlation_id`) e middleware ✅

- **Objetivo**: Logger JSON em stdout (capturado por Docker) com campos `timestamp`, `level`, `correlation_id`, `route`, `method`, `status`, `duration_ms`; middleware que aceita `X-Correlation-Id` (gera UUID se ausente) e propaga no `contextvar` durante a request.
- **Dependências**: T001
- **Critérios de aceite**:
  - `configure_logging()` chamado em `main.py` no startup
  - Middleware registra log estruturado por request com `duration_ms`
  - Header `X-Correlation-Id` ecoado na response
  - Teste: `client.get("/api/v1/health", headers={"X-Correlation-Id":"abc"})` → response com mesmo header e log com `correlation_id=abc`

### T007 — `core/errors.py` (mapeamento de exceções → HTTP) e handlers globais ✅

- **Objetivo**: Exceções de domínio (`NotFoundError`, `ForbiddenError`, `ValidationError`, `ConflictError`, `UnsupportedMediaTypeError`, `RateLimitedError`) e handlers FastAPI que retornam payloads consistentes (`{error: {code, message, correlation_id}}`).
- **Dependências**: T001
- **Critérios de aceite**:
  - Todas as exceções herdam `DomainError` com `code` estável
  - Handlers registrados em `main.py` para cada subclasse
  - Resposta 500 inesperada também é capturada (não vaza stacktrace)
  - Teste: levantar `NotFoundError` em rota dummy → `404 {"error":{"code":"not_found",...}}`

### T008 — `core/security/` esqueleto (password, jwt, refresh) — apenas estrutura ✅

- **Objetivo**: Criar os 3 módulos vazios com assinaturas definidas: `password.hash(plain) -> str`, `password.verify(plain, hashed) -> bool`; `jwt.encode_access(payload) -> str`, `jwt.decode_access(token) -> dict`; `refresh.generate() -> str`, `refresh.hash(token) -> str`.
- **Dependências**: T002
- **Critérios de aceite**:
  - Módulos compilam (funções stub `raise NotImplementedError` ou placeholder simples de bcrypt/HS256)
  - `core/security/__init__.py` re-exporta
  - Lógica real vem em T015–T021 (VS Auth)

---

## Phase 2: Infraestrutura Frontend ✅

**Objetivo**: Estabelecer a fundação do frontend React/TypeScript estrito — Vite, TanStack Query, React Router, cliente HTTP autenticado, providers globais, layout shell e tipos compartilhados.

**Independente Test**: `npm run dev` sobe a SPA; rotas `/`, `/login`, `/dashboard` placeholder renderizam; `npm run typecheck` (`tsc --noEmit`) passa em strict mode; `npm run build` produz bundle sem erro.

**Status**: ✅ Concluído — typecheck passa, build ok, 3 testes vitest passam.

### T009 — Bootstrap Vite + React 18 + TypeScript strict ✅

- **Objetivo**: Inicializar `apps/frontend/` com Vite 5, React 18+, TypeScript com `strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitOverride: true`, `exactOptionalPropertyTypes: true`; ESLint + Prettier; Vitest + Testing Library.
- **Dependências**: nenhuma
- **Critérios de aceite**:
  - `apps/frontend/package.json` declara React 18+, TS 5+, Vite 5+, Vitest, `@testing-library/react`
  - `tsconfig.json` tem todas as flags strict acima
  - `npm run dev` serve a SPA em `http://localhost:5173`
  - `npm run build` produz `dist/` sem erro
  - `npm run typecheck` passa em projeto vazio

### T010 — TanStack Query (`QueryClient`) e React Router 6 ✅

- **Objetivo**: Configurar `QueryClientProvider` em `app/providers.tsx` e `RouterProvider` em `app/router.tsx` com 5 rotas placeholder: `/`, `/login`, `/dashboard`, `/projects/:projectId`, `/s/:token`.
- **Dependências**: T009
- **Critérios de aceite**:
  - `apps/frontend/src/app/queryClient.ts` cria `QueryClient` com `staleTime: 30s`, `retry: 1`
  - `apps/frontend/src/app/router.tsx` declara as 5 rotas
  - `main.tsx` monta `Providers` (`QueryClientProvider` + `BrowserRouter`)
  - Navegação entre rotas preserva estado do `QueryClient`

### T011 — Cliente HTTP (`shared/api/`) com JWT, refresh e tipos ✅

- **Objetivo**: Wrapper `fetch` que injeta `Authorization: Bearer <access_token>`; em 401 tenta `POST /api/v1/auth/refresh` uma vez; tipos TypeScript para `User`, `Project`, `ModelFile`, `ConversionJob`, `ShareLink` derivados de `contracts/openapi.md`.
- **Dependências**: T010, T015 (precisa de `/auth/refresh` — pode ser mock durante dev)
- **Critérios de aceite**:
  - `apiClient.get/post/put/delete` aceita `path` + `body` + `signal`
  - Refresh com **rotação obrigatória**: novo `access_token` + `refresh_token`; persiste no `localStorage`/cookie
  - Tipos exportados de `shared/api/types.ts` correspondem ao OpenAPI
  - Teste unitário: 401 → tenta refresh → retry → 200

### T012 — `AuthProvider` (contexto: user, login, logout, refresh) e `useAuth` hook ✅

- **Objetivo**: Context provider que mantém `{user, accessToken, status: 'loading'|'authed'|'anonymous'}` e expõe `login`, `logout`, `register`; persiste token no `localStorage` com chave `app3d.access_token`.
- **Dependências**: T011
- **Critérios de aceite**:
  - `useAuth()` retorna `{user, status, login, logout, register}`
  - Boot: lê token, chama `GET /auth/me` (ou equivalente) para hidratar `user`
  - `status === 'loading'` exibe spinner; `'anonymous'` redireciona rotas privadas
  - Teste: provider em `Anonymous` esconde children; após `login()` re-renderiza

### T013 — Layout shell (`AppShell`): header, navegação, error boundary ✅

- **Objetivo**: Componente `<AppShell>` com header fixo, área de conteúdo, e `<ErrorBoundary>` global; rotas públicas (login, `/s/:token`) não exigem shell.
- **Dependências**: T012
- **Critérios de aceite**:
  - `<AppShell>` envolve rotas privadas; rotas públicas usam layout mínimo
  - `<ErrorBoundary>` captura exceções de render e exibe fallback amigável com `correlation_id` (se houver)
  - Logout no header chama `useAuth().logout()` e redireciona para `/login`

### T014 — `shared/components/` (Button, Card, Input, Spinner, Toaster) e design tokens ✅

- **Objetivo**: Componentes primitivos estilizados com design tokens (CSS variables) — sem biblioteca UI externa; temas light/dark.
- **Dependências**: T009
- **Critérios de aceite**:
  - Componentes acessíveis (`aria-*`, foco visível)
  - Tokens em `shared/styles/tokens.css` (cores, espaçamentos, tipografia)
  - Storybook/Vitest snapshots não exigidos no MVP
  - Teste: render de cada componente não quebra com props mínimas

---

## Phase 3: Autenticação ✅

**Objetivo**: Entregar o fluxo end-to-end de **autenticação** (registro, login, refresh, logout) — backend, persistência, JWT próprio, hash de senha, frontend com forms, validações e tratamento de erros.

**Independente Test (cobre tudo da fase)**: `POST /api/v1/auth/register` cria usuário; `POST /api/v1/auth/login` retorna `{access_token, refresh_token}`; UI `/login` autentica e redireciona para `/dashboard`; refresh rotaciona tokens; logout revoga refresh; senha fraca rejeitada com 422; rate limit por IP ativo (10 req/min).

**Status**: ✅ Concluído — 23 testes backend passando, frontend build ok.

### T015 — VS-Auth: Endpoint `POST /api/v1/auth/register` (backend) ✅

- **Objetivo**: Implementar registro criando `User` com hash bcrypt/argon2id; valida `email` único, `password ≥ 8` chars e não-comparável a email; persiste `display_name` opcional; retorna 201 com payload público (sem `password_hash`).
- **Dependências**: T005, T008
- **Critérios de aceite**:
  - `POST /api/v1/auth/register` em `features/auth/router.py`
  - 201 retorna `{id, email, display_name, created_at}`; `password_hash` nunca exposto
  - 409 quando email já existe; 422 quando senha < 8 chars; 400 quando email inválido
  - Teste integração: 3 cenários (sucesso, conflito, validação)

### T016 — VS-Auth: Endpoint `POST /api/v1/auth/login` + emissão de access+refresh (backend) ✅

- **Objetivo**: Autenticar por `email`+`password`; emitir access JWT (HS256, TTL 15 min) e refresh opaco (32 bytes hex, TTL 30 dias); persistir **hash SHA-256** do refresh; rate limit 10 req/min/IP.
- **Dependências**: T015
- **Critérios de aceite**:
  - `POST /api/v1/auth/login` retorna `{access_token, refresh_token, token_type:"Bearer", expires_in:900}`
  - 401 para credenciais inválidas (mensagem genérica — não revela se email existe)
  - 429 após 10 tentativas no mesmo IP/minuto
  - Refresh token persistido apenas como hash
  - Teste integração: login OK, credenciais inválidas, rate limit

### T017 — VS-Auth: Endpoint `POST /api/v1/auth/refresh` com rotação obrigatória (backend) ✅

- **Objetivo**: Aceitar refresh, validar hash, **rotacionar** (apresentado é invalidado, novo par é emitido); em caso de reuso de token revogado, revogar **toda a família**.
- **Dependências**: T016
- **Critérios de aceite**:
  - 200 com novo par; 401 se inválido/expirado/revogado
  - Reuso de refresh revogado → 401 + revogação de todos os tokens da família (persistir `family_id`)
  - Teste: fluxo de reuso é bloqueado

### T018 — VS-Auth: Endpoint `POST /api/v1/auth/logout` (revoga refresh) ✅

- **Objetivo**: Revogar refresh apresentado; idempotente (204 mesmo se já revogado).
- **Dependências**: T016
- **Critérios de aceite**:
  - 204 sempre (idempotente)
  - Refresh revogado não é mais aceito em `POST /auth/refresh`

### T019 — VS-Auth: `get_current_user` dependency + proteção de rotas ✅

- **Objetivo**: Dependency FastAPI que decodifica JWT, valida `exp`, busca `User` por `sub`; lança 401 se ausente/inválido/expirado; marca `request.state.user_id` para logging.
- **Dependências**: T016
- **Critérios de aceite**:
  - `Depends(get_current_user)` retorna `User`
  - 401 com payload estruturado em qualquer falha
  - Teste: rota dummy protegida retorna 401 sem token; 200 com token válido

### T020 — VS-Auth: Frontend `/login` e `/register` (forms + validação + integração) ✅

- **Objetivo**: Páginas `/login` e `/register` com forms (email, password, display_name opcional em register); validação client-side (≥ 8 chars, formato email); mensagens de erro do backend exibidas; redireciona para `/dashboard` após sucesso.
- **Dependências**: T012
- **Critérios de aceite**:
  - `/login` chama `useAuth().login(...)`; em sucesso, navega para `/dashboard`
  - `/register` chama `useAuth().register(...)`; em sucesso, auto-login
  - 401 mostra "Credenciais inválidas"; 422 mostra regras de senha
  - Rate limit (429) exibe "Muitas tentativas, tente em Xs"
  - Teste componente: form valida antes de submeter; submite com sucesso mockado

### T021 — VS-Auth: Persistência e rotação de tokens no `AuthProvider` (frontend) ✅

- **Objetivo**: Persistir `access_token` + `refresh_token` no `localStorage` (ou cookie httpOnly se backend servir; no MVP `localStorage` é aceitável); restaurar sessão no boot; refresh transparente via `apiClient`.
- **Dependências**: T011, T016
- **Critérios de aceite**:
  - Boot: lê tokens, chama endpoint `/me` (criado se necessário) para hidratar `user`
  - 401 em qualquer request → tenta refresh uma vez → retry; se falhar, logout
  - Logout limpa `localStorage` e redireciona para `/login`
  - Teste: refresh bem-sucedido preserva request original

---

## Phase 4: Upload ✅

**Objetivo**: Entregar o fluxo end-to-end de **upload** de modelos 3D (IFC, DAE, OBJ, GLB) — endpoint multipart, validação por magic bytes, persistência, UI com drag-drop, listagem por projeto.

**Independente Test**: `POST /api/v1/projects/{id}/files` (multipart) com `.ifc` válido retorna 202 com `{model_file_id, conversion_job_id, status:"pending"}`; `.stl`/`.skp` retornam 415 com mensagem; UI de upload com drag-drop aceita e mostra progresso; listar arquivos do projeto retorna ModelFiles.

**Status**: ✅ Concluído — 52 testes passando (projetos CRUD + upload + detecção de formato + exclusão).

### T022 — VS-Upload: `Project` CRUD endpoints (backend) — `features/projects/router.py`

- **Objetivo**: CRUD mínimo de Project: `POST /api/v1/projects`, `GET /api/v1/projects?archived=&cursor=&limit=`, `GET /api/v1/projects/{id}`, `PATCH /api/v1/projects/{id}`, `POST /api/v1/projects/{id}/archive`, `POST /api/v1/projects/{id}/unarchive`, `DELETE /api/v1/projects/{id}`. Apenas o owner pode mutar.
- **Dependências**: T005, T019
- **Critérios de aceite**:
  - 201 ao criar; 200 ao listar com `next_cursor`; 404/403 conforme escopo
  - Soft-delete via `archived_at`; `DELETE` remove storage, ModelFiles, ConversionJobs, ShareLinks
  - `name` trimmed; `""` rejeitado (422)
  - Teste integração: CRUD completo, ownership, paginação

### T023 — VS-Upload: `ModelFile` + `ConversionJob` entidades e `detection.py` (magic bytes)

- **Objetivo**: Criar `ModelFile` (`Mapped`) e `ConversionJob` (`Mapped`) conforme `data-model.md`; módulo `detection.py` identifica `source_format` por magic bytes (`ISO-10303-21`=IFC, `COLLADA`/XML=DAE, `#`/`v`=OBJ, `glTF`=GLB).
- **Dependências**: T005
- **Critérios de aceite**:
  - `ModelFile` tem UUID PK, FKs, `original_storage_key` (string), `content_hash` (SHA-256 hex 64), `source_format` enum
  - `ConversionJob` tem UUID PK, FK única para `ModelFile`, `status` enum, `attempts`, `last_error`, timestamps, `glb_storage_key`, `thumbnail_storage_key`
  - `detection.detect_format(headers: bytes) -> SourceFormat | None` retorna enum ou None
  - Teste unitário: 4 formatos detectados + 1 inválido retornando None

### T024 — VS-Upload: Endpoint `POST /api/v1/projects/{id}/files` (multipart, validação, hash, enfileiramento)

- **Objetivo**: Aceitar upload multipart; validar `size_bytes ≤ MAX_UPLOAD_MB * 1024 * 1024`; detectar `source_format` por magic bytes; calcular `content_hash`; persistir original via `ObjectStorage`; criar `ConversionJob(status=pending)`; enfileirar task Celery `process_model_file`; responder 202.
- **Dependências**: T022, T023, T028 (storage), T032 (worker)
- **Critérios de aceite**:
  - 202 retorna `{model_file_id, conversion_job_id, status:"pending"}`
  - 415 quando `source_format` é None ou está em `stl|rvt|dwg|dxf|skp` com mensagem clara
  - 413 quando excede `MAX_UPLOAD_MB`
  - 409 quando projeto está arquivado
  - Task enfileirada com payload conforme `contracts/openapi.md §contrato interno`
  - Teste integração: sucesso, magic bytes inválido, tamanho excedido, projeto arquivado

### T025 — VS-Upload: Endpoint `GET /api/v1/projects/{id}/files` e detalhe/remoção

- **Objetivo**: Listar `ModelFile`s do projeto (sem binário); detalhar (`GET /files/{file_id}`); deletar (`DELETE /files/{file_id}`) — remove arquivo original, GLB, thumbnail, job.
- **Dependências**: T024
- **Critérios de aceite**:
  - Lista paginada com `cursor`/`limit`; 200 com payload de `ModelFile`
  - DELETE remove do DB e do storage; 204; 404/403 conforme escopo
  - Teste integração: listar, detalhar, deletar

### T026 — VS-Upload: Frontend `/dashboard` (lista de projetos) + criar projeto modal

- **Objetivo**: Página `/dashboard` lista projetos do owner com `latest_model_file` e `is_viewable` derivados; botão "Novo projeto" abre modal com `name` + `description`; ações de arquivar/desarquivar/delete com confirmação.
- **Dependências**: T012, T022
- **Critérios de aceite**:
  - Query `useProjects()` com TanStack Query; loading skeleton; empty state
  - Modal de criação chama `POST /projects`; em sucesso, refetch e seleção
  - Ações de arquivo chamam endpoints apropriados; confirmação previne acidente
  - Teste componente: render da lista, fluxo de criação

### T027 — VS-Upload: Frontend `/projects/:projectId` (lista de ModelFiles) + UploadWidget drag-drop

- **Objetivo**: Página de detalhe do projeto mostra lista de `ModelFile`s com `source_format`, `size_bytes`, `uploaded_at`; `UploadWidget` com drag-drop aceita `.ifc|.dae|.obj|.glb`, mostra progresso por XMLHttpRequest, valida client-side (tamanho, extensão), submete multipart.
- **Dependências**: T024, T026
- **Critérios de aceite**:
  - Drag-drop destaca zona; clique abre file picker
  - Validação client: extensão ∈ `ifc|dae|obj|glb`; tamanho ≤ `MAX_UPLOAD_MB`
  - Upload via `XHR` para mostrar `progress %`; em 202, refetch da lista
  - 415 do backend exibe mensagem "Formato não suportado"
  - Teste componente: drop de arquivo válido, drop de inválido, progresso

---

## Phase 5: Storage ✅

**Objetivo**: Implementar a abstração `ObjectStorage` (Protocol) + `LocalDiskStorage` conforme `plan.md §7`, com layout físico versionado, e servir de base para Upload, Conversão e Viewer.

**Independente Test**: `LocalDiskStorage.put/get/exists/delete/open_for_read/get_size` cumprem o contrato; layout `storage/{originals,converted,thumbnails}/<project_id>/<file_id>[__<name>|<.glb|<.webp>]` é respeitado; troca futura para S3 é não-invasiva (apenas nova implementação + DI).

**Status**: ✅ Concluído — Protocol, LocalDiskStorage, keys e DI implementados.

### T028 — VS-Storage: `core/storage/base.py` (Protocol) e `LocalDiskStorage` ✅

- **Objetivo**: Definir `ObjectStorage(Protocol)` com `put`, `get`, `delete`, `exists`, `get_size`, `open_for_read`; implementar `LocalDiskStorage(root: Path)` com layout versionado.
- **Dependências**: T002
- **Critérios de aceite**:
  - Protocol com assinaturas em `core/storage/base.py`
  - `LocalDiskStorage` cria diretórios sob demanda; `put` aceita `Path` ou `BinaryIO`; `open_for_read` retorna stream
  - Path-traversal bloqueado (validação de `key` — rejeita `..`, absolutos)
  - Teste unitário: cada método com fixture `tmp_path`

### T029 — VS-Storage: `storage_key` builders (`originals`, `converted`, `thumbnails`) ✅

- **Objetivo**: Funções puras que derivam `storage_key` a partir de `project_id` e `model_file_id` (e nome sanitizado para original): `original_key(project_id, model_file_id, filename)`, `glb_key(project_id, model_file_id)`, `thumbnail_key(project_id, model_file_id)`.
- **Dependências**: T028
- **Critérios de aceite**:
  - Keys sempre **relativas** a `STORAGE_ROOT`; nunca absolutas
  - Sanitização de `filename` remove path separators, limita 255 chars
  - Teste: keys geradas batem com layout de `data-model.md §layout físico`

### T030 — VS-Storage: DI de `ObjectStorage` em `main.py` e settings ✅

- **Objetivo**: Registrar `ObjectStorage` → `LocalDiskStorage(root=Settings.STORAGE_ROOT)` no container de DI do FastAPI; expor dependency `get_storage()`.
- **Dependências**: T028, T002
- **Critérios de aceite**:
  - `app.dependency_overrides` permite trocar em testes
  - `STORAGE_BACKEND=local` (única opção no MVP; `s3` reservado)
  - Teste: dependency retorna mesma instância durante a request

### T031 — VS-Storage: Health check `/api/v1/health/ready` inspeciona storage ✅

- **Objetivo**: `GET /api/v1/health/ready` verifica DB, Redis e storage (`storage.can_write()`); 200 se tudo OK, 503 caso contrário; `/health` simples permanece liveness.
- **Dependências**: T030, T003, T004
- **Critérios de aceite**:
  - 200 quando 3/3 OK; 503 com payload estruturado listando o que falhou
  - Teste: cada dependência mockada para simular falha

---

## Phase 6: Conversão ✅

**Objetivo**: Entregar o pipeline assíncrono de **conversão** para GLB (IFC/DAE/OBJ/GLB) via Celery + Redis, usando IfcOpenShell (IFC) e Blender Headless (DAE/OBJ/GLB) — sem Trimesh/Open3D/pygltflib.

**Independente Test**: Após upload de IFC, DAE, OBJ e GLB válidos, jobs transitam `pending → running → ready`; GLB produzido contém geometria (e materiais/texturas/UVs quando aplicável); job em `failed` registra `last_error`; `POST /jobs/{id}/retry` recria job para o mesmo `ModelFile`.

**Status**: ✅ Concluído — worker Celery, pipelines IFC/mesh, endpoints de job, frontend polling, 17 testes passando.

### T032 — VS-Conv: Worker Celery (`conversion/worker.py`) e `process_model_file` task

- **Objetivo**: Instanciar `Celery(app=..., broker=Settings.REDIS_URL, backend=Settings.REDIS_URL)`; definir task `process_model_file(job_id, model_file_id, project_id, source_format, original_storage_key)` que orquestra o pipeline e atualiza o `ConversionJob`.
- **Dependências**: T005, T030
- **Critérios de aceite**:
  - `celery -A app.conversion.worker worker --loglevel=info` sobe
  - Task atualiza `pending → running` (com `started_at`, `attempts++`) antes do trabalho; `running → {ready|failed}` no fim
  - Update condicional: `WHERE status='pending' OR (status='failed' AND attempts < MAX_CONVERSION_ATTEMPTS)` evita corrida
  - `last_error` populado em `failed`; `duration_ms` em ambos terminais
  - Teste integração: task em modo eager (`CELERY_TASK_ALWAYS_EAGER=True`) percorre os 4 formatos

### T033 — VS-Conv: Pipeline IFC (`conversion/pipelines/ifc.py`) — IfcOpenShell + Blender

- **Objetivo**: Extrair geometria com materiais/UVs via IfcOpenShell (preservando `IfcSurfaceStyle` e texturas embarcadas); produzir intermediário (`.glb` ou mesh Blender); normalizar e exportar GLB final via Blender headless.
- **Dependências**: T032
- **Critérios de aceite**:
  - `pipelines/ifc.run(input_path, output_glb_path)` produz GLB não-vazio
  - Materiais e UVs preservados (validação best-effort com fixture IFC real)
  - Falha de extração → levanta `ConversionError` com mensagem acionável
  - Teste com fixture IFC pequeno: `len(mesh.polygons) > 0` no GLB resultante

### T034 — VS-Conv: Pipeline mesh (`conversion/pipelines/mesh.py`) — Blender headless para DAE/OBJ/GLB

- **Objetivo**: Importar DAE (`bpy.ops.wm.collada_import`), OBJ (`bpy.ops.wm.obj_import`) ou GLB (`bpy.ops.import_scene.gltf`) via Blender headless; normalizar eixos/escala; exportar `model.glb` binário.
- **Dependências**: T032
- **Critérios de aceite**:
  - `pipelines/mesh.run(input_path, source_format, output_glb_path)` produz GLB não-vazio para os 3 formatos
  - Normalização de eixos aplicada (decisão documentada em `common.py`)
  - Teste: fixtures DAE/OBJ/GLB pequenas → GLB válido

### T035 — VS-Conv: `conversion/pipelines/common.py` — normalização e orquestração

- **Objetivo**: Funções compartilhadas: `normalize_axes(mesh)`, `scale_to_unit(mesh, target=1.0)`, `dispatch(source_format) -> Callable` que mapeia para o pipeline certo; logging estruturado.
- **Dependências**: T033, T034
- **Critérios de aceite**:
  - `dispatch("ifc")` → `pipelines.ifc.run`; `"dae"|"obj"|"glb"` → `pipelines.mesh.run`
  - `dispatch("stl")` → `NotImplementedError` (defesa em profundidade)
  - Teste: cada formato chega ao pipeline certo

### T036 — VS-Conv: Endpoint `GET /api/v1/jobs/{job_id}` (status do job)

- **Objetivo**: Consultar status e metadados de um `ConversionJob`; apenas o owner (via `Project`) tem acesso.
- **Dependências**: T032
- **Critérios de aceite**:
  - 200 com payload `{id, model_file_id, status, attempts, last_error, started_at, finished_at, duration_ms, glb_url, thumbnail_url}` — URLs apenas quando `ready`
  - 404/403 conforme escopo
  - Teste integração: job `pending`, `running`, `ready`, `failed`

### T037 — VS-Conv: Endpoint `POST /api/v1/jobs/{job_id}/retry` (recria job)

- **Objetivo**: Se o job está em `failed`, criar **novo** `ConversionJob` (status `pending`) para o mesmo `ModelFile` e enfileirar task; 409 se status ≠ `failed`.
- **Dependências**: T036
- **Critérios de aceite**:
  - 202 com novo `job_id`; 409 caso o job atual não esteja em `failed`
  - `ModelFile` permanece imutável (apenas novo job é criado)
  - Teste integração: retry após falha, 409 em outros estados

### T038 — VS-Conv: Frontend polling de status (`useJobStatus`) + indicador visual

- **Objetivo**: Hook `useJobStatus(jobId)` que faz poll a cada 2s com TanStack Query enquanto status ∈ `{pending, running}`; UI exibe barra de progresso indeterminada + estado textual.
- **Dependências**: T027, T036
- **Critérios de aceite**:
  - Polling para automaticamente em `ready` ou `failed`
  - `failed` exibe `last_error` (sanitizado) e botão "Tentar novamente"
  - Teste componente: simulação de transições

---

## Phase 7: Thumbnail

**Objetivo**: Entregar a **geração de thumbnail WebP** (800×600 default) como parte do pipeline de conversão — render via Blender headless com câmera automática enquadrando o bounding box.

**Independente Test**: Após qualquer upload válido, `thumbnail.webp` é gerado em `storage/thumbnails/<project_id>/<file_id>.webp`; dimensões 800×600; `Content-Type: image/webp` ao servir.

### T039 — VS-Thumb: `conversion/pipelines/thumbnail.py` — render WebP via Blender ✅

- **Objetivo**: Receber GLB, posicionar câmera automática enquadrando bounding box, renderizar em 800×600 (configurável), salvar como WebP (qualidade 80).
- **Dependências**: T034
- **Critérios de aceite**:
  - `pipelines/thumbnail.render(glb_path, output_webp_path, size=(800,600))` produz arquivo não-vazio
  - WebP válido (header `RIFF....WEBP`)
  - Modelos sem geometria → `ConversionError("empty_mesh")`
  - Teste com fixture GLB: thumbnail tem dimensões 800×600

### T040 — VS-Thumb: Integração no worker — thumbnail após GLB pronto ✅

- **Objetivo**: Após `running → ready` na task, chamar `thumbnail.render(glb_path, thumb_path)`; persistir `thumbnail_storage_key`; em falha de thumbnail, **falhar o job inteiro** (não aceitar GLB sem thumbnail).
- **Dependências**: T032, T039
- **Critérios de aceite**:
  - Job só vira `ready` se GLB **e** thumbnail foram gerados
  - Falha de thumbnail → `failed` com `last_error` específico
  - Teste: pipeline completo → ambos artefatos no storage

### T041 — VS-Thumb: Frontend `<Thumbnail>` com fallback e skeleton ✅

- **Objetivo**: Componente `<Thumbnail modelFileId>` que resolve URL via `GET /s/{token}/thumbnail.webp` (público) ou via job (privado); exibe skeleton enquanto imagem não carrega; fallback para placeholder.
- **Dependências**: T014, T049 (precisa de share token — pode usar placeholder até share existir)
- **Critérios de aceite**:
  - `<img>` com `loading="lazy"`, `decoding="async"`, `alt` descritivo
  - Erro de carga exibe placeholder
  - Teste componente: render com src válido e inválido

### T042 — VS-Thumb: Constante `THUMBNAIL_SIZE` configurável via `Settings` ✅

- **Objetivo**: Adicionar `THUMBNAIL_SIZE_W`, `THUMBNAIL_SIZE_H` em `Settings`; padrão 800×600; lido pelo pipeline de thumbnail.
- **Dependências**: T002, T039
- **Critérios de aceite**:
  - Override via env funciona
  - Teste: thumbnail gerado com tamanho customizado

---

## Phase 8: Viewer

**Objetivo**: Entregar a **visualização 3D** no navegador usando `<model-viewer>` (Google) com GLB canônico — controles orbit/zoom/fullscreen, fallback de loading e erro.

**Independente Test**: Com um job `ready`, o GLB é servindo com `Content-Type: model/gltf-binary` e HTTP Range support; `<model-viewer src="..." camera-controls auto-rotate>` renderiza o modelo e responde a interações básicas.

### T043 — VS-Viewer: Endpoint `GET /s/{token}/model.glb` com Range requests ✅

- **Objetivo**: Servir o GLB do storage autenticando pela posse do token; suportar HTTP `Range: bytes=` (essencial para `<model-viewer>`); `Content-Type: model/gltf-binary`; `Cache-Control: public, max-age=3600`.
- **Dependências**: T049 (token), T028
- **Critérios de aceite**:
  - 200 sem Range; 206 com `Content-Range` quando Range é solicitado
  - 404 se token inválido/revogado
  - 416 se Range inválido
  - Teste integração: GET simples, GET com Range, GET com Range inválido
- **Nota Sprint 4**: Implementado como endpoint autenticado `GET /api/v1/files/{id}/glb` (sem share token, conforme restrição "não implementar compartilhamento"). Suporta Range requests, Cache-Control, Accept-Ranges. Teste em `test_viewer.py::TestGlbEndpoint`.

### T044 — VS-Viewer: Endpoint `GET /s/{token}/thumbnail.webp` ✅

- **Objetivo**: Servir o thumbnail com `Content-Type: image/webp`; `Cache-Control: public, max-age=86400`.
- **Dependências**: T049, T040
- **Critérios de aceite**:
  - 200 com bytes do WebP; 404 quando thumbnail ausente (job não `ready`)
  - 404 quando token inválido/revogado
  - Teste integração: sucesso, token inválido, job não `ready`
- **Nota Sprint 4**: Implementado como endpoint autenticado `GET /api/v1/files/{id}/thumbnail` (sem share token). Retorna `image/webp` com Cache-Control. Teste em `test_viewer.py::TestThumbnailEndpoint`.

### T045 — VS-Viewer: Página `/s/:token` (SPA route pública, sem auth) ✅

- **Objetivo**: Página pública renderizada pela SPA que recebe `token` da URL, chama `/manifest`, monta `<model-viewer>` com `src={glb_url}` e `poster={thumbnail_url}`.
- **Dependências**: T013, T054
- **Critérios de aceite**:
  - Rota `/s/:token` é pública (não passa por `AppShell`/auth)
  - Loading enquanto manifest não chega; erro 404 com mensagem amigável
  - `<model-viewer>` configurado com `camera-controls`, `auto-rotate` (opcional), `ar` (configurável em T059)
  - Teste componente: render com manifest válido e 404
- **Nota Sprint 4**: Implementado como rota autenticada `/viewer/:fileId` (dentro do AppShell, com auth). Usa `useViewerMetadata` hook para polling de status. Exibe estados de loading, erro, conversão pendente/running/failed. Componente `ViewerPage.tsx`.

### T046 — VS-Viewer: Componente `<ModelViewer>` wrapper com props e fallback ✅

- **Objetivo**: Wrapper sobre `<model-viewer>` que aceita props tipadas (`src`, `poster`, `alt`, `arModes`, `autoRotate`); expõe eventos (`onLoad`, `onError`); fallback visual se Web Components não carregarem.
- **Dependências**: T014
- **Critérios de aceite**:
  - TypeScript: props tipadas com discriminated unions
  - Carrega o web component dinamicamente em SSR/CSR (no MVP CSR-only)
  - `onError` propaga erro para `<ErrorBoundary>`
  - Teste componente: render com props mínimas, com todas as props

### T047 — VS-Viewer: Manifest endpoint `GET /s/{token}/manifest` (público, autenticado-por-token) ✅

- **Objetivo**: Retornar JSON com `model_file_id`, `format: "glb"`, `glb_url`, `thumbnail_url`, `project_name`, `uploader_display_name`.
- **Dependências**: T049
- **Critérios de aceite**:
  - 200 com payload; 404 se token inválido/revogado
  - 409 (ou 404) se job não está `ready` ainda
  - Teste integração: sucesso, token revogado, job não `ready`
- **Nota Sprint 4**: Implementado como endpoint autenticado `GET /api/v1/files/{id}/viewer` retornando `ViewerResponse` (model_file_id, project_id, filename, source_format, status, glb_url, thumbnail_url, last_error). Schema em `schemas.py`. Teste em `test_viewer.py::TestViewerEndpoint`.

### T048 — VS-Viewer: Frontend integra manifest com `<ModelViewer>` ✅

- **Objetivo**: Hook `useShareManifest(token)` chama `/manifest`; resultado alimenta `<ModelViewer>`; exibe `<Thumbnail>` como poster.
- **Dependências**: T045, T046, T047
- **Critérios de aceite**:
  - Estados: loading, error, ready; ready renderiza o viewer
  - 404 do manifest exibe página dedicada
  - Teste componente: fluxo end-to-end com mock do manifest
- **Nota Sprint 4**: Implementado com `useViewerMetadata(fileId)` hook (TanStack Query) que faz polling do endpoint `/api/v1/files/{id}/viewer`. `ViewerPage` integra `ModelViewer` com `src` (GLB URL) e `poster` (thumbnail URL). Estados: loading (Spinner), erro, conversão pendente/running/failed, ready.

---

## Phase 9: Compartilhamento

**Objetivo**: Permitir ao **owner** criar, listar e revogar links públicos de visualização — tokens opacos ≥ 128 bits de entropia, gerados server-side com CSPRNG, persistidos como hash.

**Independente Test**: `POST /api/v1/projects/{id}/shares` retorna 201 com `{token, url: "/s/{token}"}`; `GET /shares` lista; `POST /shares/{token}/revoke` revoga idempotentemente; token revogado retorna 404 em todos endpoints públicos; **sem `expires_at`/`view_count`** (R-17, R-18).

**Status**: ✅ Concluído — ShareLink model, service, router, 19 testes passando. Endpoints: `POST /api/v1/files/{id}/share`, `GET /api/v1/shares`, `DELETE /api/v1/shares/{id}`.

### T049 — VS-Share: `ShareLink` entidade e `POST /api/v1/projects/{id}/shares` (criar) ✅

- **Objetivo**: Criar `ShareLink` com token opaco (32 bytes hex = 256 bits de entropia ≥ 128), apontando para um `model_file_id` específico (não para o Project); persistir `created_by` (audit); retornar URL pública `/s/{token}`.
- **Dependências**: T005, T022, T024 (precisa ModelFile existente)
- **Critérios de aceite**:
  - 201 com `{id, token, url, model_file_id, created_at}`
  - 422 se `model_file_id` não pertence ao projeto
  - 409 se o job do `model_file` não está `ready`
  - Token jamais logado em texto puro
  - Teste integração: criação, validação de escopo, job não `ready`

### T050 — VS-Share: `GET /api/v1/projects/{id}/shares` (listar) ✅

- **Objetivo**: Listar `ShareLink`s do projeto do owner, com `revoked_at` incluído.
- **Dependências**: T049
- **Critérios de aceite**:
  - 200 com lista paginada; 403 se não-owner
  - Tokens não são ecoados (apenas `id` e metadados — o token só foi retornado na criação)
  - Teste integração: listar vazio, listar com múltiplos

### T051 — VS-Share: `POST /api/v1/shares/{token}/revoke` (revogar) ✅

- **Objetivo**: Marcar `revoked_at` se ainda não estava revogado; idempotente (204).
- **Dependências**: T049
- **Critérios de aceite**:
  - 204 sempre; apenas o owner do projeto do `model_file` pode revogar (autenticação via JWT + ownership check)
  - Após revogação, todos endpoints `/s/{token}/*` retornam 404
  - Teste integração: revogar, revogar de novo (idempotente), 404 nos endpoints públicos

### T052 — VS-Share: `resolve_token(token)` service (compartilhado por viewer) ✅

- **Objetivo**: Service puro que recebe token, faz hash, busca `ShareLink`; retorna `None` se inválido/revogado; usado por TODOS os endpoints `/s/{token}/*`.
- **Dependências**: T049
- **Critérios de aceite**:
  - Hash SHA-256 do token (mesmo algoritmo de `refresh.hash`)
  - 1 query ao DB, com índice em `token_hash`
  - Teste: token válido, token revogado, token inexistente

### T053 — VS-Share: Frontend `ShareDialog` (criar link, copiar URL, revogar) ✅

- **Objetivo**: Modal no detalhe do projeto: "Criar link para este modelo" → chama endpoint → exibe URL para copiar (botão "Copiar") e listar links existentes com botão "Revogar".
- **Dependências**: T027, T049
- **Critérios de aceite**:
  - Lista links existentes com status (ativo/revogado) e data
  - Criar link só habilitado para ModelFiles com job `ready`
  - Copiar URL usa `navigator.clipboard` com feedback
  - Revogar pede confirmação
  - Teste componente: criar, copiar (mock), revogar

---

## Phase 10: Visualização Pública

**Objetivo**: Entregar a **página pública** `/s/{token}` servida pela SPA — HTML do frontend + endpoints autenticados-por-token, sem passar por JWT.

**Independente Test**: Abrir `/s/{token}` em janela anônima: manifest carrega, thumbnail aparece como poster, `<model-viewer>` renderiza o GLB, controles orbit/zoom/fullscreen funcionam; em token revogado, página exibe "Link inválido ou expirado".

**Status**: ✅ Concluído — Public viewer router (manifest, GLB, thumbnail), SharePage frontend com model-viewer, meta tags OG, página de erro 404.

### T054 — VS-Public: `GET /s/{token}` serve a SPA (HTML estático + fallback para index) ✅

- **Objetivo**: Endpoint público que serve `index.html` da SPA; nginx (em produção) ou FastAPI (em dev) fazem o roteamento; o frontend faz a chamada a `/manifest` client-side.
- **Dependências**: T045, T049
- **Critérios de aceite**:
  - 200 com `Content-Type: text/html`
  - Assets estáticos servidos corretamente (`/assets/...`)
  - Rota SPA captura `/*` para sub-rotas (no MVP, configurado em nginx)
  - Teste integração: GET retorna HTML esperado

### T055 — VS-Public: Página de erro 404 para share inválido ✅

- **Objetivo**: UI dedicada quando `/manifest` retorna 404: "Link inválido ou expirado" com ilustração.
- **Dependências**: T045
- **Critérios de aceite**:
  - Componente `<ShareNotFound>` consistente com design system
  - Link "Voltar ao início" → `/`
  - Teste componente: renderiza com 404 mockado

### T055a — VS-Public: PWA-lite manifest + meta tags OG (preview ao compartilhar) ✅

- **Objetivo**: Adicionar `<meta property="og:title">`, `og:image` (thumbnail), `og:type=website` populados dinamicamente via injeção client-side para preview em mensageria.
- **Dependências**: T045, T048
- **Critérios de aceite**:
  - Meta tags injetadas após `/manifest` resolver
  - `og:image` aponta para `/s/{token}/thumbnail.webp`
  - Teste: meta tags presentes no DOM após mount

### T056 — VS-Public: CORS e CSP para endpoints `/s/*` ✅

- **Objetivo**: Configurar CORS permissivo para `/s/*` (públicos); CSP permitindo `<model-viewer>` e `blob:` para WebXR/AR.
- **Dependências**: T031, T054
- **Critérios de aceite**:
  - Preflight `OPTIONS /s/{token}/manifest` retorna CORS headers
  - CSP permite scripts da SPA; permite conexões para `/s/`
  - Teste: preflight + GET com `Origin` válido

### T057 — VS-Public: Rate limit em endpoints públicos (proteção de hot-linking) ✅

- **Objetivo**: Limite por IP em `/s/{token}/*` para mitigar scraping/abuse — 60 req/min/IP por token.
- **Dependências**: T054
- **Critérios de aceite**:
  - 429 com `Retry-After` após excesso
  - Não aplicar em `/s/{token}` (a página) — apenas nos assets
  - Teste: 61ª request em <1min retorna 429

### T058 — VS-Public: Logs de acesso público estruturados (sem PII) ✅

- **Objetivo**: Log de cada request a `/s/{token}/*` com `share_link_id`, `model_file_id`, `route`, `status`, `duration_ms`; **sem** IP, user-agent, ou token em texto puro.
- **Dependências**: T006, T052
- **Critérios de aceite**:
  - Log estruturado em JSON; campos sensíveis ausentes
  - `correlation_id` propagado
  - Teste: log gerado com campos esperados; sem PII

---

## Phase 11: AR

**Objetivo**: Habilitar a **visualização em Realidade Aumentada** via `<model-viewer>` — `ar` attr, `ar-modes="webxr scene-viewer quick-look"`; banner HTTPS em dev; fallback gracioso quando AR não disponível.

**Independente Test**: Em Android Chrome sobre HTTPS, tocar no ícone AR abre o Scene Viewer com o GLB; em iOS Safari sobre HTTPS, abre Quick Look; em desktop, ícone AR fica oculto.

### T059 — VS-AR: Atributos AR no `<ModelViewer>` (`ar`, `ar-modes`, `ar-scale`) ✅

- **Objetivo**: Quando o ambiente é HTTPS (e o dispositivo suporta), expor `ar` no `<model-viewer>`; configurar `ar-modes="webxr scene-viewer quick-look"` e `ar-scale="auto"`.
- **Dependências**: T046
- **Critérios de aceite**:
  - `ar` attr presente quando `window.isSecureContext === true`
  - `ar-modes` configurado para os 3 alvos
  - Componente aceita prop `arEnabled: boolean` para testes
  - Teste componente: render com/sem `arEnabled`

### T060 — VS-AR: Banner HTTPS em ambiente de desenvolvimento ✅

- **Objetivo**: Quando `window.location.protocol === 'http:'` (apenas dev), exibir banner: "AR requer HTTPS" com instrução para usar `https://localhost` ou tunnel.
- **Dependências**: T045
- **Critérios de aceite**:
  - Banner visível apenas em HTTP; oculto em HTTPS
  - Instrução clara (ex.: `mkcert`, Cloudflare Tunnel)
  - Não bloqueia uso do viewer 3D (apenas avisa)
  - Teste componente: render com/sem HTTPS

### T061 — VS-AR: Detecção de suporte AR e fallback visual ✅

- **Objetivo**: Detectar suporte via `navigator.xr?.isSessionSupported('immersive-ar')` (WebXR) e `aria` em iOS; ocultar botão AR se nenhum modo disponível; exibir tooltip explicativo.
- **Dependências**: T059
- **Critérios de aceite**:
  - WebXR check assíncrono; resultado cacheado na sessão
  - Botão AR oculto em desktop sem suporte
  - Tooltip "Seu navegador não suporta AR" quando aplicável
  - Teste: mock de `navigator.xr` para simular suporte/ausência

### T062 — VS-AR: Documentação rápida de teste AR (Android + iPhone) ✅

- **Objetivo**: Seção em `docs/` com checklist: ngrok/Caddy tunnel, `PUBLIC_BASE_URL` HTTPS, abrir no celular, validar Scene Viewer (Android) e Quick Look (iOS).
- **Dependências**: T059
- **Critérios de aceite**:
  - Doc em `docs/ar-testing.md` com passos numerados
  - Comando exato para expor backend em HTTPS (ex.: `ngrok http 8000`)
  - Troubleshooting comum (certificado inválido, etc.)
  - Não inclui código

---

## Phase 12: Testes

**Objetivo**: Consolidar a **estratégia de testes** por feature vertical slice — unitários para services/pipelines, integração para endpoints HTTP, frontend com Vitest+Testing Library; gate qualitativo (nenhuma feature sem testes) conforme Constituição §9 e §11.

**Independente Test (cobre tudo)**: `pytest apps/backend` passa com cobertura mínima; `npm test` em `apps/frontend` passa; quickstart `specs/001-ifc-mvp-platform/quickstart.md §0–§5` executa E2E com sucesso (upload IFC/DAE/OBJ/GLB → share → visualização anônima).

**Status**: ✅ Concluído — 155 testes backend passando, frontend vitest ok, checklists criadas.

### T063 — VS-Test: Backend `pytest` setup (conftest, fixtures, DB de teste) ✅

- **Objetivo**: `apps/backend/tests/conftest.py` com fixtures: `db_session` (schema separado por teste), `client` (httpx.AsyncClient + ASGITransport), `storage` (tmp_path), `celery_eager` (`CELERY_TASK_ALWAYS_EAGER=True`).
- **Dependências**: T001, T005
- **Critérios de aceite**:
  - DB de teste isolado (schema dedicado ou container efêmero)
  - Cada teste roda em transação revertida no fim
  - `pytest -q` descobre e roda 0 testes ainda (suite vazia é OK)
  - Doc em `apps/backend/tests/README.md`

### T064 — VS-Test: Testes de integração por feature (auth, projects, models, conversion, sharing, viewer) ✅

- **Objetivo**: Cobertura por feature dos endpoints definidos em `contracts/openapi.md`: auth (4 endpoints), projects (7), model files (4), jobs (2), shares (3), viewer público (4). Mínimo: happy path + 1 erro por endpoint.
- **Dependências**: cada endpoint do seu slice respectivo
- **Critérios de aceite**:
  - ≥ 30 testes de integração passando
  - Cobertura mínima por feature: 80% lines em `service.py` e `router.py`
  - Teste de ownership: usuário B não lê recurso de A (403)
  - `pytest --cov=app --cov-report=term-missing` exibe métricas

### T065 — VS-Test: Testes unitários de pipelines (IFC, mesh, thumbnail) e `core/storage` ✅

- **Objetivo**: Testes unitários dos pipelines de conversão (com fixtures mínimas) e do `LocalDiskStorage`; usam Blender headless em ambiente controlado.
- **Dependências**: T033, T034, T039, T028
- **Critérios de aceite**:
  - Cada pipeline tem ≥ 2 testes (sucesso + erro recuperável)
  - `LocalDiskStorage` cobre put/get/exists/delete/open_for_read/get_size + path-traversal
  - Fixtures de IFC/DAE/OBJ/GLB pequenas (~10–50 KB) versionadas em `tests/fixtures/`

### T066 — VS-Test: Frontend `vitest` setup + testes de hooks e componentes críticos ✅

- **Objetivo**: `apps/frontend/src/test/setup.ts` configura `@testing-library/react`; testes para `useAuth`, `useProjects`, `useJobStatus`, `<UploadWidget>`, `<ModelViewer>`, `<ShareDialog>`, `<SharePage>`.
- **Dependências**: T011, T012, T027, T038, T045
- **Critérios de aceite**:
  - `npm test` roda a suíte com ≥ 70% de aprovação
  - Mocks de `apiClient` evitam rede real
  - Componentes críticos têm teste de render e interação

### T067 — VS-Test: Gate qualitativo — nenhuma feature sem testes (checklist pre-merge) ✅

- **Objetivo**: Documento `apps/backend/tests/CHECKLIST.md` e `apps/frontend/CHECKLIST.md` que o agent preenche antes de marcar qualquer feature como concluída: code, unit tests, integration tests, tests executed, validated. Alinhado à Constituição §11.
- **Dependências**: T064, T065, T066
- **Critérios de aceite**:
  - Template markdown com 5 checkboxes por feature
  - Vinculado ao PR template (se houver)
  - Reforça: testes falhando = feature não-concluída

---

## Phase 13: Docker ✅

**Objetivo**: Empacotar toda a stack (PostgreSQL, Redis, API, worker, frontend via nginx) em **containers reprodutíveis** via Docker Compose, com isolamento de dependências pesadas (Blender, IfcOpenShell) no worker.

**Independente Test**: `docker compose up` sobe os 5 serviços; `backend` responde em `:8000`, `frontend` em `:5173` (dev) ou `:8080` (prod via nginx), `worker` consome fila; volumes para Postgres, Redis e `storage/` persistem entre reboots.

**Status**: ✅ Concluído — todos os Dockerfiles, docker-compose.yml, nginx.conf e redis.conf implementados. Build contexts corrigidos.

### T068 — VS-Docker: `infra/docker/postgres/` (Dockerfile + init scripts) ✅

- **Objetivo**: Imagem baseada em `postgres:16-alpine`; init scripts para criar database `app3d` e role dedicado; volume nomeado `pg_data`.
- **Dependências**: nenhuma
- **Critérios de aceite**:
  - `docker compose up postgres` inicia e fica healthy em <10s
  - `psql` com credenciais de env conecta
  - Volume `pg_data` persiste dados entre `down`/`up`

### T069 — VS-Docker: `infra/docker/redis/` (Dockerfile + config mínimo) ✅

- **Objetivo**: Imagem `redis:7-alpine`; `maxmemory-policy noeviction` (fila não pode perder jobs); AOF habilitado para durabilidade; volume `redis_data`.
- **Dependências**: nenhuma
- **Critérios de aceite**:
  - `docker compose up redis` healthy em <5s
  - `redis-cli ping` retorna `PONG`
  - `INFO persistence` mostra `aof_enabled:1`

### T070 — VS-Docker: `infra/docker/worker/` (Blender + IfcOpenShell — imagem dedicada) ✅

- **Objetivo**: Imagem Python com Blender headless e IfcOpenShell instalados; entrypoint `celery -A app.conversion.worker worker`; monta volume `storage/` (read/write) compartilhado com backend.
- **Dependências**: T032, T068, T069
- **Critérios de aceite**:
  - Build com `docker build -t app3d-worker -f infra/docker/worker/Dockerfile .`
  - `docker compose up worker` consome tasks de Redis
  - Sem `trimesh`, `open3d`, `pygltflib` na imagem (verificar com `pip freeze`)

### T071 — VS-Docker: `infra/docker/backend/` (FastAPI API) ✅

- **Objetivo**: Imagem Python slim; instala deps do backend; entrypoint `uvicorn app.main:app --host 0.0.0.0 --port 8000`; expõe `/api/v1/*`; monta volume `storage/` (read/write).
- **Dependências**: T001, T068, T069
- **Critérios de aceite**:
  - `docker compose up backend` healthy em <15s
  - `GET /api/v1/health` retorna 200 dentro do container
  - Variáveis de env injetadas de `.env` ou Compose

### T072 — VS-Docker: `infra/docker/frontend/` (build Vite + nginx) + `docker-compose.yml` final ✅

- **Objetivo**: Multi-stage: build com Node 20 (`npm run build`); runtime com nginx alpine servindo `dist/`; nginx faz proxy reverso para `/api/v1/*` e `/s/*` no backend. `docker-compose.yml` final une os 5 serviços + volumes.
- **Dependências**: T071
- **Critérios de aceite**:
  - `docker compose up` sobe a stack completa
  - `http://localhost:8080` (nginx) carrega a SPA; `/api/v1/health` retorna 200 via proxy
  - `/s/{token}` resolve corretamente via proxy
  - Hot reload de dev: `docker compose -f docker-compose.dev.yml up` com bind mounts
  - `docker compose down -v` limpa volumes

---

## Dependências & Ordem de Execução

### Dependências entre Fases (Vertical Slices)

```text
Fase 1 (Infraestrutura Backend) ─┐
                                   ├─→ Fase 3 (Auth)         ─┐
Fase 2 (Infraestrutura Frontend) ─┘                            │
                                                              ├─→ Fase 4 (Upload) ─┐
                                                              │                    │
                                                              │                    ├─→ Fase 5 (Storage)
                                                              │                    │     [Storage é transversal]
                                                              │                    │
                                                              │                    ├─→ Fase 6 (Conversão) ─┐
                                                              │                    │                       │
                                                              │                    │                       ├─→ Fase 7 (Thumbnail)
                                                              │                    │                       │
                                                              │                    └─→ Fase 8 (Viewer) ←────┘
                                                              │                         │
                                                              │                         ├─→ Fase 9 (Compartilhamento)
                                                              │                         │
                                                              │                         └─→ Fase 10 (Visualização Pública)
                                                              │                              │
                                                              │                              └─→ Fase 11 (AR)
                                                              │
                                                              ├─→ Fase 12 (Testes)  [consolida tudo]
                                                              │
                                                              └─→ Fase 13 (Docker)  [empacota tudo]
```

### Regra geral

- **Fases 1 + 2** (infraestrutura) **bloqueiam** todas as demais.
- **Fase 3** (Auth) é pré-requisito para qualquer endpoint autenticado (Fases 4–9).
- **Fase 5** (Storage) é **transversal**: seu Protocol + LocalDiskStorage é pré-requisito para Upload (T024), Conversão (T032), Thumbnail (T040), Viewer (T043–T044). T028–T031 podem ser desenvolvidos em paralelo com Fase 3.
- **Fase 7** (Thumbnail) **depende da Fase 6** (Conversão) porque o thumbnail é gerado a partir do GLB produzido.
- **Fase 8** (Viewer) **depende da Fase 6** (precisa do GLB) **e da Fase 9** (precisa de token para servir).
- **Fase 9** (Compartilhamento) **depende da Fase 4** (ModelFile existente) e **bloqueia** a Fase 10.
- **Fase 10** (Visualização Pública) **depende da Fase 9** (token) **e da Fase 8** (viewer).
- **Fase 11** (AR) **depende da Fase 10** (página pública funcional).
- **Fase 12** (Testes) é **cross-cutting**: deve ser executada incrementalmente em cada fase, com T067 como gate final.
- **Fase 13** (Docker) é **cross-cutting**: imagens podem ser construídas incrementalmente, mas o `docker-compose.yml` final consolida tudo.

### Dependências Dentro de Cada Vertical Slice

- **Backend-first**: Implementar `service.py` antes de `router.py`; testar `service.py` (unit) antes de `router.py` (integration).
- **Contract-first**: Schemas Pydantic (`schemas.py`) derivam de `contracts/openapi.md`; validação acontece em borda.
- **Frontend-last**: Páginas só podem ser implementadas após os endpoints do backend existirem (podem ser mockados durante dev).

---

## Oportunidades de Paralelismo

### Paralelização entre Vertical Slices (após dependências)

```bash
# Após Fase 1+2 (T001–T014) e Fase 3 (T015–T021):
# Lançar em paralelo:
T022 Project CRUD (backend)
T028–T031 Storage (backend)         [Storage é transversal]
T032 Worker Celery + task skeleton  [pode ser desenvolvido em paralelo com T022–T031]

# Após Fase 4 (T022–T027) e Fase 5 (T028–T031) e Fase 6 (T032–T038):
# Lançar em paralelo:
T039–T042 Thumbnail pipeline         [só depende de T032]
T049–T053 Share backend              [depende de T022, T024]

# Após Fase 9 (T049–T053) e Fase 8 (T043–T048) prontas:
# Lançar em paralelo:
T054–T058 Visualização pública
T059–T062 AR
```

### Paralelização Dentro de uma Fase

Exemplo **Fase 1 (T001–T008)** — após T001, todos os outros podem rodar em paralelo:

```bash
# Lançar juntos:
T002 core/config.py
T006 core/logging.py + middleware
T007 core/errors.py
T008 core/security/ esqueleto
```

Exemplo **Fase 3 (T015–T021)** — após T015–T016 prontos, frontend pode começar em paralelo:

```bash
# Backend:
T017 /auth/refresh
T018 /auth/logout
T019 get_current_user dependency
# Frontend (paralelo):
T020 /login + /register pages
T021 AuthProvider persistence
```

---

## Estratégia de Implementação

### MVP Mínimo (Fases 1+2+3+4+5+6+7+9+10)

Caminho feliz: usuário registra → faz login → cria projeto → faz upload de `.ifc`/`.dae`/`.obj`/`.glb` → worker converte → owner gera link → cliente anônimo abre `/s/{token}` e visualiza.

**Incrementos testáveis independentemente**:
- Após Fase 1+2: `docker compose up backend` → `/health` 200
- Após Fase 3: `POST /auth/register` + `POST /auth/login` + UI login funcional
- Após Fase 4+5: `POST /projects/{id}/files` aceita upload e persiste (job fica `pending` mas worker ainda não processa)
- Após Fase 6+7: job transita para `ready` com GLB + thumbnail
- Após Fase 9+10: `POST /projects/{id}/shares` → `/s/{token}` carrega modelo

### Entrega Incremental (sugestão de Sprints)

| Sprint | Fases | Entregável |
|---|---|---|
| Sprint 1 | 1, 2, 3 | Backend + frontend bootstrap + autenticação funcional |
| Sprint 2 | 4, 5 | Upload + storage (job fica pending) |
| Sprint 3 | 6, 7 | Conversão + thumbnail end-to-end (GLB pronto no storage) |
| Sprint 4 | 8, 9, 10 | Viewer + share + página pública |
| Sprint 5 | 11, 12, 13 | AR + testes + Docker final |

### Estratégia Paralela de Time

Com 2–3 desenvolvedores:
1. **Dev A (Backend)**: Fases 1, 3, 4, 5, 6, 7, 9
2. **Dev B (Frontend)**: Fases 2, 4 (UI), 8, 9 (UI), 10, 11
3. **Dev C (Worker/Infra)**: Fases 5, 6, 13 (em paralelo com ambos)

A **Fase 12 (Testes)** é responsabilidade de quem implementa cada slice — **não delegar para o final**.

---

## Notas

- **Total de tarefas**: 72 (T001–T072, com T055a inserida)
- **Tarefas paralelizáveis** (`[P]`): ~28 (cerca de 39%)
- **Nenhuma tarefa introduz funcionalidade fora do escopo do MVP** (Constituição §12): `view_count`, `metadata`, `expires_at`, STL/RVT/DWG/DXF/SKP, Trimesh/Open3D/pygltflib, DDD/CQRS/Event Sourcing, Admin endpoint, USDZ server-side, BIM tree
- **Senhas ≥ 8 chars** com hash bcrypt/argon2id; **JWT HS256** com chave em env
- **Refresh tokens**: 32 bytes hex, persistidos como hash SHA-256, com **rotação obrigatória** e revogação de família em caso de reuso
- **Rate limit**: 10 req/min/IP em `/auth/*`; 60 req/min/IP/token em `/s/{token}/*`
- **Limites**: `MAX_UPLOAD_MB` (default 100 MB no MVP, ajustável), `MAX_CONVERSION_TIMEOUT_S` (default 600s), `MAX_CONVERSION_ATTEMPTS` (default 3)
- **Storage layout versionado**: `storage/{originals,converted,thumbnails}/<project_id>/<file_id>[__<name>|<.glb|<.webp>]` (ver `data-model.md §layout físico`)
- **Sem 3xx redirects** em rotas `/files/` ou `/s/`
- **`PUBLIC_BASE_URL` deve ser HTTPS** para testes de AR em dispositivo
- **GLB é o único formato interno canônico**; DAE/OBJ/GLB passam por Blender; IFC por IfcOpenShell+Blender
- **Pipeline preserva materiais > texturas > UVs > metadados BIM** (Constituição §4)
- **Nenhuma tarefa implementa fora do escopo sem approval humano** (Constituição §10)
- **Tarefa só é concluída quando código + testes + execução + validação estão ok** (Constituição §11)

---

## Done When

- [x] Todas as 13 fases listadas com objetivos, dependências, critérios de aceite
- [x] 72 tarefas geradas com IDs sequenciais (T001–T072) e paths exatos
- [x] Nenhuma tarefa classificada por camada técnica (Models/Repositories/Services/Controllers)
- [x] Formato `- [ ] [ID] [P?] [VS?] Descrição` respeitado
- [x] Grafo de dependências explícito
- [x] Oportunidades de paralelismo identificadas por fase
- [x] Estratégia de implementação (MVP + sprints + time paralelo) documentada
- [x] Sem código gerado (apenas especificação)
- [x] Conformidade com Constituição v2.0.0 (especialmente §10 e §12)
- [x] Campos por tarefa (objetivo, dependências, critérios de aceite) presentes em todas as 72 tarefas
