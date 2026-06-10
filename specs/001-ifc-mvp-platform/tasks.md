# Tasks: Arch3DAR — Correção MVP IFC → AR (Android + iPhone)

**Input**: Design documents from `specs/001-ifc-mvp-platform/`

**Prerequisites**: plan.md, spec.md (correction scope in plan.md supersedes auth/MinIO portions), research.md, data-model.md, contracts/openapi.md, quickstart.md

**Tests**: Included — plan and acceptance criteria explicitly require automated tests for upload, GLB/USDZ conversion, and file download.

**Organization**: Tasks grouped by correction user story (US1–US4). Auth, dashboard, and MinIO are out of scope.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to correction user story (US1–US4)
- Every task includes an exact file path

## User Story Mapping (Correction Scope)

| Story | Priority | Goal | Independent Test |
|---|---|---|---|
| **US1** | P1 | Upload IFC → conversão GLB + USDZ → persistência em `/data` | `POST /upload` retorna `Ready`; arquivos existem em `/data/projects/{id}/` |
| **US2** | P1 | Servir GLB/USDZ/thumbnail diretamente + Share API + QR | `GET /files/...` retorna 200, MIME correto, sem `Location` header |
| **US3** | P1 | Visualização Web 3D no link público | Abrir `/s/{token}` — thumbnail + GLB renderizam com orbit/zoom |
| **US4** | P1 | AR Android (Scene Viewer) + iPhone (Quick Look) | Tap AR em Android e iPhone sem "Object could not be opened" |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Remover MinIO do stack e preparar volume local compartilhado

- [x] T001 Remove `minio` service, `minio_data` volume, and MinIO env vars from `app/docker-compose.yml`; add `project_data` volume mounted at `/data` on `backend` and `converter`
- [x] T002 [P] Replace MinIO variables with `DATA_ROOT=/data` and document `PUBLIC_BASE_URL` (HTTPS) in `app/.env.example`
- [x] T003 [P] Remove `Minio` NuGet package reference from `app/backend/Backend.csproj`
- [x] T004 [P] Remove `minio` dependency from `app/converter/requirements.txt`; drop trimesh/pxr if replaced by `usd_from_gltf`
- [x] T005 [P] Update `app/README.md` to document local storage layout `/data/projects/{id}/` and removal of MinIO
- [x] T006 [P] Add `build-converter` and `verify-no-minio` targets to `Makefile` if useful for CI smoke checks

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura core que bloqueia todas as user stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [x] T007 Create `app/backend/Infrastructure/LocalFileStorage.cs` with `EnsureProjectDir`, `WriteFile`, `ResolvePath`, `FileExists` under `{DATA_ROOT}/projects/{id}/`
- [x] T008 [P] Create `app/backend/Infrastructure/ModelContentTypeMiddleware.cs` mapping `.glb` → `model/gltf-binary`, `.usdz` → `model/vnd.usdz+zip`, `.png` → `image/png`
- [x] T009 Update `app/backend/Domain/Project.cs` and `app/backend/Domain/ProjectStatus.cs` per `data-model.md` (DataDirectory, file names, no MinIO keys)
- [x] T010 Update `app/backend/Infrastructure/AppDbContext.cs` entity configuration for simplified `projects` table
- [x] T011 Update `app/backend/Migrations/20260610000000_Initial.cs` to match simplified schema (drop `share_links`/Identity if present)
- [x] T012 Create `app/converter/usd_converter.py` wrapping `usd_from_gltf` CLI with timeout and error handling
- [x] T013 Update `app/converter/Dockerfile` to install/bake `usd_from_gltf` binary (e.g. from `marlon360/usd-from-gltf` stage) on Linux
- [x] T014 Refactor `app/converter/converter_service.py` to write `original.ifc`, `model.glb`, `model.usdz`, `thumbnail.png` to `/data/projects/{id}/` and remove all MinIO code
- [x] T015 Delete `app/backend/Infrastructure/MinioService.cs` and remove all references
- [x] T016 Update `app/backend/Infrastructure/HttpModelConverter.cs` to call converter sidecar and return local relative paths (not MinIO keys)

**Checkpoint**: Foundation ready — converter writes to `/data`, backend can read paths, MinIO removed from code

---

## Phase 3: User Story 1 — Upload + Conversão GLB/USDZ (Priority: P1) 🎯 MVP

**Goal**: `POST /upload` aceita IFC, executa pipeline IfcConvert → GLB → `usd_from_gltf` → USDZ, persiste em disco local

**Independent Test**: `curl -F file=@sample.ifc http://localhost:5001/upload` → `status: Ready`; `ls /data/projects/{id}/` mostra os 4 arquivos

### Tests for User Story 1

- [x] T017 [P] [US1] Create `app/tests/backend/Integration/UploadConversionTests.cs` — POST `/upload` with `app/tests/backend/Integration/Fixtures/sample.ifc`, assert `Ready`, assert files on disk
- [x] T018 [P] [US1] Add converter smoke test in `app/converter/test_usd_converter.py` — GLB fixture → non-empty valid USDZ zip

### Implementation for User Story 1

- [x] T019 [US1] Refactor `POST /upload` in `app/backend/Program.cs` to save IFC via `LocalFileStorage` instead of MinIO
- [x] T020 [US1] Wire synchronous `HttpModelConverter.ConvertAsync` in `app/backend/Program.cs` after IFC persist; update project status `Converting` → `Ready`/`Failed`
- [x] T021 [US1] Enforce mandatory USDZ in `app/backend/Program.cs` — call `MarkFailed` if `model.usdz` missing or zero bytes (no GLB-only fallback)
- [x] T022 [US1] Update `app/backend/Dockerfile` to set `DATA_ROOT=/data`, mount-compatible with converter volume
- [x] T023 [P] [US1] Update `app/converter/converter_service.py` response contract to return `{ glbPath, usdzPath, thumbnailPath, durationMs }` per `contracts/openapi.md`

**Checkpoint**: Upload end-to-end works; GLB + USDZ gerados localmente

---

## Phase 4: User Story 2 — Entrega Direta de Arquivos + Share + QR (Priority: P1)

**Goal**: Assets servidos via `GET /files/{projectId}/...` sem redirect; Share API retorna URLs same-origin absolutas

**Independent Test**: `curl -sI /files/{id}/model.usdz` → `200`, `Content-Type: model/vnd.usdz+zip`, sem header `Location`

### Tests for User Story 2

- [x] T024 [P] [US2] Create `app/tests/backend/Integration/FileServingTests.cs` — assert GLB/USDZ Content-Type, `Accept-Ranges` on GLB, no `Location` header, 404 for unknown id

### Implementation for User Story 2

- [x] T025 [US2] Implement `GET /files/{projectId}/model.glb` in `app/backend/Program.cs` using `Results.File()` + `LocalFileStorage.ResolvePath`
- [x] T026 [P] [US2] Implement `GET /files/{projectId}/model.usdz` in `app/backend/Program.cs` with `model/vnd.usdz+zip`
- [x] T027 [P] [US2] Implement `GET /files/{projectId}/thumbnail.png` in `app/backend/Program.cs`
- [x] T028 [US2] Update `GET /share/{token}` in `app/backend/Program.cs` to return absolute same-origin URLs (`{PUBLIC_BASE_URL}/files/{id}/model.glb`) — no presigned MinIO URLs
- [x] T029 [US2] Register `ModelContentTypeMiddleware` in `app/backend/Program.cs` before file-serving routes
- [x] T030 [US2] Remove MinIO upstream and `/glb-files/`, `/thumbnails/` locations from `app/nginx/nginx.conf`; add `location /files/` → `proxy_pass http://backend/files/` with `proxy_redirect off`
- [x] T031 [P] [US2] Ensure `GET /share/{token}/qr` in `app/backend/Program.cs` returns SVG QR pointing to `{PUBLIC_BASE_URL}/s/{token}`

**Checkpoint**: curl downloads GLB/USDZ directly; share JSON has no minio hostnames

---

## Phase 5: User Story 3 — Visualização Web 3D (Priority: P1)

**Goal**: Cliente abre `/s/{token}` e vê thumbnail + modelo 3D interativo (orbit, zoom, pan)

**Independent Test**: Abrir link público no browser — `<model-viewer>` carrega GLB, poster mostra thumbnail, controles funcionam

### Tests for User Story 3

- [x] T032 [P] [US3] Update `app/frontend/src/__tests__/SharePage.test.tsx` — mock share API, assert `<model-viewer>` renders with `src` and `poster`
- [x] T033 [P] [US3] Skipped — `adminBoundary.test.ts` not present; routes already limited to HomePage + SharePage

### Implementation for User Story 3

- [x] T034 [US3] Update `app/frontend/src/pages/HomePage.tsx` (upload) to `POST /upload` and navigate to `/s/{token}` on success
- [x] T035 [US3] Simplify `app/frontend/src/App.tsx` routes to `/` (HomePage/upload) and `/s/:token` (SharePage) only; remove dashboard/login routes
- [x] T036 [P] [US3] Delete or stub unused pages: `app/frontend/src/pages/DashboardPage.tsx`, `app/frontend/src/pages/ProjectDetailPage.tsx`, `app/frontend/src/pages/UploadPage.tsx` if superseded by HomePage
- [x] T037 [US3] Update `app/frontend/vite.config.ts` dev proxy for `/upload`, `/share/`, `/files/` → backend
- [x] T038 [US3] Verify `app/frontend/src/pages/SharePage.tsx` uses share API `glbUrl`/`thumbnailUrl` and shows loading/not-found states

**Checkpoint**: Web viewer works desktop and mobile browser without AR

---

## Phase 6: User Story 4 — AR Android + iPhone Quick Look (Priority: P1)

**Goal**: AR funciona em Android (Scene Viewer) e iPhone (Quick Look) via `ios-src` + USDZ válido + HTTPS

**Independent Test**: Manual checklist quickstart §6 — iPhone Quick Look abre sem "Object could not be opened"

### Tests for User Story 4

- [x] T039 [P] [US4] Create `app/frontend/src/__tests__/ModelViewerAr.test.tsx` — assert `ios-src` attribute set when `usdzUrl` provided; `ar-modes` includes `quick-look` first

### Implementation for User Story 4

- [x] T040 [US4] Update `app/frontend/src/pages/SharePage.tsx` — `ios-src={usdzUrl}`, `ar-modes="quick-look scene-viewer webxr"`, `auto-rotate`, `camera-controls`, `shadow-intensity="1"`, `exposure="1"`
- [x] T041 [US4] Hide or disable AR affordance in `app/frontend/src/pages/SharePage.tsx` when `usdzUrl` is null; keep 3D viewer as fallback
- [x] T042 [US4] Show HTTPS-required banner in `app/frontend/src/pages/SharePage.tsx` when `window.location.protocol !== 'https:'`
- [x] T043 [US4] Configure `PUBLIC_BASE_URL` as HTTPS in `app/docker-compose.yml` and `app/.env.example` for production AR testing
- [x] T044 [US4] Add `types` for `model.usdz` and `model/gltf-binary` in `app/nginx/nginx.conf` `mime.types` include or explicit `types` block if needed
- [x] T045 [P] [US4] Remove dead AR code from `app/frontend/src/components/ModelViewer.tsx` if SharePage is the sole viewer; ensure no admin imports

**Checkpoint**: AR manual test passes on Android Chrome and iOS Safari over HTTPS

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, validação final, zero MinIO

- [x] T046 [P] Remove `app/frontend/src/auth/useCurrentUser.ts`, `app/frontend/src/api/client.ts` auth helpers, and unused components (`ShareDialog.tsx`, `StatusBadge.tsx`) if no longer referenced
- [x] T047 [P] Update `app/tests/backend/Unit/ProjectStateTransitionTests.cs` for `Uploading`/`Converting`/`Ready`/`Failed` states
- [x] T048 Run `make test-backend` and fix failures in `app/tests/backend/` (net10.0; 10/10 passing)
- [x] T049 [P] Run `make test-frontend` and fix failures in `app/frontend/src/__tests__/`
- [ ] T050 Run quickstart validation scenarios §0–§4 from `specs/001-ifc-mvp-platform/quickstart.md` (boot, upload, disk check, curl MIME)
- [x] T051 [P] Grep entire `app/` for `minio`, `MinIO`, `presign`, `S3` — remove or document any remaining references
- [x] T052 Run `make audit-bim` to confirm FR-031/SC-008 compliance in user-facing surfaces
- [ ] T053 Complete manual AR checklist in `specs/001-ifc-mvp-platform/quickstart.md` §6 on real Android + iPhone devices

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) — BLOCKS all stories
    ↓
Phase 3 (US1: Upload+Convert) — required before US2 file serving has data
    ↓
Phase 4 (US2: File serving) — required before US3/US4 can load assets
    ↓
Phase 5 (US3: Web viewer) ─┐
    ↓                      ├→ can overlap once US2 complete
Phase 6 (US4: AR) ─────────┘
    ↓
Phase 7 (Polish)
```

### User Story Dependencies

- **US1** → **US2**: files must exist before serving endpoints matter
- **US2** → **US3/US4**: viewer and AR need same-origin `/files/` URLs
- **US3** and **US4** can proceed in parallel after US2 (different files: SharePage web vs AR attrs)

### Parallel Opportunities

**Phase 1** (all [P]): T002, T003, T004, T005, T006 in parallel after T001

**Phase 2**: T008 parallel with T007; T012/T013 parallel with backend tasks after T007

**Phase 3**: T017, T018 parallel; T023 parallel with T019–T022

**Phase 4**: T024 parallel with prep; T026, T027, T031 parallel after T025

**Phase 5–6**: Frontend test tasks [P]; US3 and US4 frontend edits are mostly sequential on `SharePage.tsx` — coordinate to avoid conflicts

---

## Parallel Example: User Story 2

```bash
# After T025 lands, launch in parallel:
Task T026: "Implement GET /files/{projectId}/model.usdz in app/backend/Program.cs"
Task T027: "Implement GET /files/{projectId}/thumbnail.png in app/backend/Program.cs"
Task T031: "Ensure GET /share/{token}/qr in app/backend/Program.cs"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1) — upload produces GLB + USDZ on disk
3. Complete Phase 4 (US2) — files downloadable with correct MIME
4. **STOP and VALIDATE**: quickstart §1–§4 via curl

### Incremental Delivery

1. US1 + US2 → backend pipeline complete (no UI needed for curl validation)
2. Add US3 → web viewer demo
3. Add US4 → AR on real devices over HTTPS
4. Phase 7 → production-ready cleanup

### Suggested MVP Scope

Minimum shippable correction: **Phase 1 + 2 + 3 + 4** (backend complete). Frontend (US3 + US4) required for acceptance criteria 5–6 (AR on devices).

---

## Notes

- Total tasks: **53**
- Per story: Setup 6, Foundational 10, US1 7, US2 8, US3 7, US4 7, Polish 8
- USDZ failure must fail the whole upload (no silent GLB-only fallback)
- Never use 302/307/308 for `/files/` routes
- `PUBLIC_BASE_URL` must be HTTPS for real-device AR tests
- Commit after each phase checkpoint
