# Implementation Plan: Arch3DAR — Correção MVP IFC → AR (Android + iPhone)

**Branch**: `main` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md) (correção MVP — ver **Correction Scope** abaixo)

**Input**: Correção do fluxo AR no iPhone, remoção de MinIO/S3, armazenamento local, geração USDZ e simplificação do sistema.

## Correction Scope (supersedes portions of spec.md)

O projeto já funciona para visualização Web e AR no Android. O iPhone falha com *"Object could not be opened"* no Quick Look. A causa raiz é a combinação de:

1. Ausência de `ios-src` apontando para um USDZ válido (ou USDZ malformado).
2. Entrega de assets via presigned MinIO URLs (redirects / hostnames incompatíveis com Quick Look).
3. Content-Type incorreto ou ausente para `.glb` / `.usdz`.

Esta correção **remove** do escopo ativo:

- MinIO, S3, object storage, buckets, abstrações de storage distribuído
- Autenticação, usuários, dashboard, multi-tenant, publish idempotente em duas etapas

Esta correção **mantém**:

- Upload IFC → conversão GLB + USDZ + thumbnail
- Link público + QR Code
- Visualização Web (`<model-viewer>`)
- AR Android (Scene Viewer) e iPhone (Quick Look)

## Summary

Arch3DAR passa a ser um MVP mínimo: upload de IFC, conversão síncrona no sidecar Python (IfcConvert → GLB → `usd_from_gltf` → USDZ), persistência em disco local (`/data/projects/{projectId}/`), e entrega direta de arquivos pelo backend/nginx sem redirects. O frontend tem duas páginas (`UploadPage`, `ViewerPage`/`SharePage`) com `<model-viewer>` configurado com `ios-src` obrigatório. PostgreSQL permanece apenas para metadados do projeto (token público, status, paths relativos). Nenhum serviço MinIO no `docker-compose`.

## Technical Context

**Language/Version**: C# 13 / .NET 9 (`net9.0`) backend; TypeScript 5 / React 18 + Vite frontend; Python 3.11 converter sidecar.

**Primary Dependencies**:
- Backend: EF Core 9 + Npgsql, Serilog, QRCoder, Kestrel static file middleware (custom content-types).
- Frontend: `@google/model-viewer@3.3`, `react-router-dom@6`.
- Converter: IfcOpenShell `IfcConvert`, **Google `usd_from_gltf`** (GLB→USDZ), Pillow (thumbnail fallback).
- Infra: nginx (TLS termination + reverse proxy), Docker Compose.

**Storage**:
- **Local filesystem** (Docker volume `project_data` → `/data`):
  ```
  /data/projects/{projectId}/
    original.ifc
    model.glb
    model.usdz
    thumbnail.png
  ```
- PostgreSQL 16: tabela `projects` com paths relativos e `public_token` (hex, 32 chars).
- **Nenhum** MinIO, S3, presigned URL, bucket.

**Testing**:
- Backend integration: upload IFC → assert GLB/USDZ exist on disk → GET `/files/{id}/model.glb` e `/files/{id}/model.usdz` retornam 200 com Content-Type correto, sem redirect.
- Converter unit: GLB sample → USDZ non-empty, zip válido.
- Frontend: Vitest para props do `ModelViewer` (`ios-src` presente quando `usdzUrl` definido).
- Manual checklist (quickstart §8): Android + iPhone AR via QR e link direto.

**Target Platform**: Linux server (Docker). Clientes: Safari iOS 15+, Chrome Android 10+ (ARCore). Quick Look exige HTTPS válido.

**Project Type**: Web application simplificada (2 páginas + API mínima).

**Performance Goals**:
- Upload + conversão síncrona: ≤ 5 min para IFC ~50 MB (mesmo SC-001, fluxo único).
- GET `/files/...` p95 < 50 ms (servido localmente, sem proxy S3).
- Página pública carrega thumbnail + GLB em < 10 s em 4G.

**Constraints**:
- Max upload 100 MB (env `MAX_IFC_MB`).
- Conversão timeout 120 s (env `CONVERSION_TIMEOUT_S`).
- **Sem redirects** (302/307/308) em URLs de assets — Quick Look falha com redirect.
- Content-Type obrigatório: `model/gltf-binary` (GLB), `model/vnd.usdz+zip` (USDZ), `image/png` (thumbnail).
- HTTPS obrigatório para AR; banner no frontend quando `location.protocol !== 'https:'`.
- USDZ obrigatório para marcar projeto `ready`; falha na geração USDZ = projeto `failed`.

**Scale/Scope**:
- 1 upload por vez aceitável no MVP; sem fila distribuída.
- Endpoints finais: `POST /upload`, `GET /viewer/{id}`, `GET /files/{id}/model.glb`, `GET /files/{id}/model.usdz`, `GET /files/{id}/thumbnail.png`, `GET /qrcode/{id}`, `GET /health`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Clean Code & MVP Pragmatism** | ✅ Pass | Remoção de MinIO, auth e dashboard reduz superfície. Filesystem + EF é o mínimo para metadados. `usd_from_gltf` escolhido por compatibilidade iOS, não por abstração prematura. |
| **II. Meaningful Naming & Structure** | ✅ Pass | `LocalFileStorage`, `UsdConverter`, paths `projects/{id}/model.glb`. Endpoints espelham paths de disco. |
| **III. Small Units & Single Responsibility** | ✅ Pass | `LocalFileStorage` (I/O disco), `UsdConverter` (GLB→USDZ), endpoints finos em `Program.cs` ou `Api/Endpoints/`. |
| **IV. Tests Mirror Structure** | ✅ Pass | Testes em `app/tests/backend/Integration/` para pipeline upload→files; `app/tests/frontend/Unit/` para model-viewer props. |
| **V. Self-Documenting Code & Minimal Comments** | ✅ Pass | Comentários apenas em middleware de Content-Type e restrição "no redirect". |

**Route Boundary update**: Com remoção do dashboard, a fronteira admin/público simplifica para `UploadPage` (sem model-viewer) vs `SharePage`/`ViewerPage` (único lugar com AR). O canary `adminBoundary.test.ts` permanece válido.

**Constitution re-check after Phase 1 design**: All 5 principles pass. Simplificação alinha com MVP-pragmatism.

## Project Structure

### Documentation (this feature)

```text
specs/001-ifc-mvp-platform/
├── plan.md              # This file
├── research.md          # Phase 0 — decisões corrigidas (local storage, USDZ, Quick Look)
├── data-model.md        # Phase 1 — Project simplificado, filesystem layout
├── contracts/
│   └── openapi.md       # Phase 1 — API mínima sem auth/MinIO
├── quickstart.md        # Phase 1 — validação E2E + checklist manual AR
└── spec.md              # Spec original (parcialmente superseded por Correction Scope)
```

### Source Code (repository root)

```text
app/
├── backend/
│   ├── Domain/
│   │   ├── Project.cs
│   │   └── ProjectStatus.cs
│   ├── Infrastructure/
│   │   ├── AppDbContext.cs
│   │   ├── LocalFileStorage.cs      # NEW: read/write /data/projects/{id}/*
│   │   ├── ModelContentTypeMiddleware.cs  # NEW: GLB/USDZ MIME
│   │   ├── HttpModelConverter.cs
│   │   ├── QrCodeService.cs
│   │   └── CorrelationIdMiddleware.cs
│   ├── Program.cs                   # POST /upload, GET /files/*, GET /viewer/*
│   └── Dockerfile
│
├── converter/
│   ├── converter_service.py         # IfcConvert + usd_from_gltf (UsdConverter)
│   ├── usd_converter.py             # NEW: subprocess wrapper usd_from_gltf
│   ├── requirements.txt
│   └── Dockerfile                   # bake usd_from_gltf binary
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx         # UploadPage
│   │   │   └── SharePage.tsx        # ViewerPage com ios-src
│   │   └── App.tsx
│   └── nginx.conf                   # proxy /api + /files sem redirect
│
├── nginx/                           # TLS termination, proxy_pass direto
├── docker-compose.yml               # 4 services: postgres, backend, converter, frontend+nginx
│                                    # NO minio
└── tests/
    ├── backend/Integration/
    └── frontend/Unit/
```

**Structure Decision**: Mantém layout `app/{backend,frontend,converter,tests}/`. Remove serviço `minio` e código `MinioService`. Volume compartilhado `project_data:/data` entre `backend` e `converter`.

## Complexity Tracking

Nenhuma violação da constituição. A remoção de MinIO e auth **reduz** complexidade em relação ao plano anterior.

## Migration from current state (ordered)

1. **Converter**: trocar upload MinIO por escrita em `/data/projects/{id}/`; substituir trimesh+OpenUSD por `usd_from_gltf`; falhar se USDZ vazio.
2. **Backend**: remover `Minio` package, `MinioService`, presigned URLs; adicionar `LocalFileStorage` + endpoints `GET /files/{projectId}/{file}` com `Results.File()` (sem redirect).
3. **Share API**: retornar URLs absolutas same-origin (`https://host/files/{id}/model.glb`) em vez de presigned MinIO.
4. **docker-compose**: remover `minio` service/volume; montar `project_data:/data` em backend + converter.
5. **nginx**: `location /files/` → `proxy_pass http://backend:5000/files/` sem `return 302`; validar `proxy_redirect off`.
6. **Frontend**: garantir `ios-src={usdzUrl}` e `ar-modes="quick-look scene-viewer webxr"`; esconder AR se `usdzUrl` null.
7. **Tests**: integration sem Testcontainers MinIO; assert Content-Type e ausência de `Location` header.
8. **Cleanup**: deletar referências MinIO em `.env.example`, README, specs antigas.

## Acceptance Criteria (correction)

1. IFC enviado via `POST /upload`.
2. `model.glb` e `model.usdz` gerados em `/data/projects/{id}/`.
3. QR Code gerado (`GET /qrcode/{token}`).
4. Android abre AR (Scene Viewer).
5. iPhone abre AR sem *"Object could not be opened"* (Quick Look).
6. Nenhum serviço MinIO no projeto.
7. Arquivos servidos diretamente (`200 OK`, Content-Type correto, sem redirect).
