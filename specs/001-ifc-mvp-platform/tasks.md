# Tasks: Arch3DAR — IFC/SketchUp → Web 3D + AR MVP

**Input**: Design documents from `specs/001-ifc-mvp-platform/`

**Prerequisites**: plan.md, spec.md (clarifications 2026-06-10), research.md (R-11…R-21), data-model.md, contracts/openapi.md, quickstart.md

**Tests**: Included — SC-007 and quickstart §9 require automated E2E coverage for upload, conversion, and file serving.

**Organization**: Phases 1–8 delivered IFC correction + WebP thumbnail (complete). **Phase 7 (SKP) superseded** — Blender stock has no `io_sketchup`. **Phase 10** migrates to DAE/OBJ SketchUp workflow per R-21.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to spec user story (US1, US2, US3)
- Every task includes an exact file path

## User Story Mapping

| Story | Priority | Goal | Independent Test |
|---|---|---|---|
| **US1** | P1 | Upload `.ifc`, `.dae`, or `.obj` → GLB + USDZ + thumbnail → public link + QR; reject `.skp` | `POST /upload` → `Ready`; `/data/projects/{id}/` has all artifacts; `.skp` → 415 |
| **US2** | P1 | Client opens `/s/{token}` — WebP poster + interactive 3D viewer | Incognito browser: orbit/zoom/fullscreen work |
| **US3** | P1 | AR on Android (Scene Viewer) + iPhone (Quick Look via USDZ) | Tap AR on mobile over HTTPS — no Quick Look error |

---

## Phase 1: Setup — Local Storage (Complete ✅)

**Purpose**: Remove MinIO; shared `/data` volume

- [x] T001 Remove `minio` service and add `project_data:/data` volume in `app/docker-compose.yml`
- [x] T002 [P] Replace MinIO env with `DATA_ROOT=/data`, `PUBLIC_BASE_URL` in `app/.env.example`
- [x] T003 [P] Remove `Minio` package from `app/backend/Backend.csproj`
- [x] T004 [P] Remove MinIO/trimesh deps from `app/converter/requirements.txt`
- [x] T005 [P] Document local storage in `app/README.md`
- [x] T006 [P] Add Makefile targets for converter build / MinIO audit

---

## Phase 2: Foundational — Core Infrastructure (Complete ✅)

**Purpose**: LocalFileStorage, USDZ pipeline, simplified schema

- [x] T007 Create `app/backend/Infrastructure/LocalFileStorage.cs`
- [x] T008 [P] Create `app/backend/Infrastructure/ModelContentTypeMiddleware.cs`
- [x] T009 Update `app/backend/Domain/Project.cs` and `ProjectStatus.cs` per data-model
- [x] T010 Update `app/backend/Infrastructure/AppDbContext.cs`
- [x] T011 Update `app/backend/Migrations/20260610000000_Initial.cs`
- [x] T012 Create `app/converter/usd_converter.py`
- [x] T013 Update `app/converter/Dockerfile` with `usd_from_gltf`
- [x] T014 Refactor `app/converter/converter_service.py` for local disk output
- [x] T015 Delete `app/backend/Infrastructure/MinioService.cs`
- [x] T016 Update `app/backend/Infrastructure/HttpModelConverter.cs`
- [x] T016a Create `app/converter/glb_normalize.py` and integrate in `app/converter/converter_service.py`

**Checkpoint**: IFC pipeline writes GLB/USDZ/thumbnail to `/data/projects/{id}/`

---

## Phase 3: User Story 1 — Upload + Conversion IFC (Complete ✅)

**Goal**: `POST /upload` accepts IFC → IfcConvert → normalize → USDZ

**Independent Test**: `curl -F file=@sample.ifc /upload` → `Ready`; files on disk

- [x] T017 [P] [US1] Create `app/tests/backend/Integration/UploadConversionTests.cs`
- [x] T018 [P] [US1] Create `app/converter/test_usd_converter.py`
- [x] T019 [US1] Refactor `POST /upload` in `app/backend/Program.cs` for `LocalFileStorage`
- [x] T020 [US1] Wire `HttpModelConverter.ConvertAsync` with status transitions in `app/backend/Program.cs`
- [x] T021 [US1] Enforce mandatory USDZ — `MarkFailed` if missing in `app/backend/Program.cs`
- [x] T022 [US1] Update `app/backend/Dockerfile` with `DATA_ROOT=/data`
- [x] T023 [P] [US1] Align converter response contract in `app/converter/converter_service.py`

---

## Phase 4: User Story 2 — File Serving + Share API (Complete ✅)

**Goal**: Direct `GET /files/...` without redirect; share JSON with asset URLs

**Independent Test**: `curl -sI /files/{id}/model.usdz` → 200, correct MIME, no `Location`

- [x] T024 [P] [US2] Create `app/tests/backend/Integration/FileServingTests.cs`
- [x] T025 [US2] Implement `GET /files/{projectId}/model.glb` in `app/backend/Program.cs`
- [x] T026 [P] [US2] Implement `GET /files/{projectId}/model.usdz` in `app/backend/Program.cs`
- [x] T027 [P] [US2] Implement `GET /files/{projectId}/thumbnail.png` in `app/backend/Program.cs`
- [x] T028 [US2] Update `GET /share/{token}` with same-origin URLs in `app/backend/Program.cs`
- [x] T029 [US2] Register `ModelContentTypeMiddleware` in `app/backend/Program.cs`
- [x] T030 [US2] Update `app/nginx/nginx.conf` — `/files/` proxy, no redirect
- [x] T031 [P] [US2] Implement `GET /share/{token}/qr` in `app/backend/Program.cs`

---

## Phase 5: User Story 2 — Web Viewer (Complete ✅)

**Goal**: `/s/{token}` renders thumbnail poster + `<model-viewer>`

**Independent Test**: Public link loads GLB with orbit/zoom in browser

- [x] T032 [P] [US2] Update `app/frontend/src/__tests__/SharePage.test.tsx`
- [x] T034 [US2] Update `app/frontend/src/pages/HomePage.tsx` for upload flow
- [x] T035 [US2] Simplify routes in `app/frontend/src/App.tsx`
- [x] T036 [P] [US2] Remove unused dashboard pages from `app/frontend/src/pages/`
- [x] T037 [US2] Update dev proxy in `app/frontend/vite.config.ts`
- [x] T038 [US2] Verify loading/error states in `app/frontend/src/pages/SharePage.tsx`

---

## Phase 6: User Story 3 — AR Android + iPhone (Complete ✅)

**Goal**: Scene Viewer + Quick Look via `ios-src` + valid USDZ

**Independent Test**: AR opens on Android Chrome and iOS Safari over HTTPS

- [x] T039 [P] [US3] Create `app/frontend/src/__tests__/ModelViewerAr.test.tsx`
- [x] T040 [US3] Configure AR attrs in `app/frontend/src/pages/SharePage.tsx`
- [x] T041 [US3] Hide AR when `usdzUrl` null in `app/frontend/src/pages/SharePage.tsx`
- [x] T042 [US3] HTTPS banner in `app/frontend/src/pages/SharePage.tsx`
- [x] T043 [US3] Configure `PUBLIC_BASE_URL` HTTPS in `app/docker-compose.yml`
- [x] T044 [US3] MIME types for GLB/USDZ in `app/nginx/nginx.conf`
- [x] T045 [P] [US3] Clean up `app/frontend/src/components/ModelViewer.tsx` if unused

---

## Phase 7: SKP Support — SUPERSEDED ⚠️

> **Obsolete (2026-06-10)**: Tasks T054–T066 implemented broken SKP path (`io_sketchup` unavailable in Blender 4.2.3). Do not extend. **Phase 10** replaces with DAE/OBJ workflow (R-21).

- [x] T054 [P] Add Blender 4.2 LTS and headless deps to `app/converter/Dockerfile`
- [x] T055 [P] Create `app/converter/skp_to_glb.py` — **to be removed in T091**
- [x] T056 [P] Extract IFC steps into `app/converter/ifc_pipeline.py`
- [x] T057 [US1] Update `app/converter/converter_service.py` — **to be updated in T090**
- [x] T058–T066 SKP backend/frontend/tests — **to be replaced in Phase 10**

---

## Phase 8: Thumbnail WebP Migration (Complete ✅)

**Goal**: Replace `thumbnail.png` with `thumbnail.webp` via Blender render

**Independent Test**: `curl -sI /files/{id}/thumbnail.webp` → 200, `image/webp`

- [x] T067 [P] Create `app/converter/render_thumbnail.py`
- [x] T068 [US1] Update `app/converter/converter_service.py` — Blender thumbnail after normalize
- [x] T069 [P] [US2] Add `.webp` → `image/webp` in `app/backend/Infrastructure/ModelContentTypeMiddleware.cs`
- [x] T070 [US2] Replace thumbnail route with `thumbnail.webp` in `app/backend/Program.cs`
- [x] T071 [US2] Update `GET /share/{token}` thumbnail URL in `app/backend/Program.cs`
- [x] T072 [P] [US2] Update `app/frontend/src/pages/SharePage.tsx` poster to WebP
- [x] T073 [P] Update default `ThumbnailFileName` in `app/backend/Domain/Project.cs`
- [x] T074 [P] [US2] Update `app/tests/backend/Integration/FileServingTests.cs` — `image/webp`
- [x] T075 [P] [US1] Update `app/tests/backend/Integration/UploadConversionTests.cs` — `thumbnail.webp`
- [x] T076 [P] Create `app/converter/test_render_thumbnail.py`

---

## Phase 9: Service Abstractions (Complete ✅)

- [x] T077 [P] Create `app/backend/Services/IModelConversionService.cs`
- [x] T078 [P] Create `app/backend/Services/IFileStorageService.cs`
- [x] T079 Register `IModelConversionService` → `HttpModelConverter` in `app/backend/Program.cs`
- [x] T080 [P] Update `app/README.md` — **to be refreshed in T104**
- [x] T081 [P] Update `app/converter/converter_service.py` OpenAPI docstring
- [x] T082–T084 Run automated test suites (pre-DAE migration baseline)
- [x] T087 [P] Grep `app/` for `thumbnail.png` — remove stale references

---

## Phase 10: User Story 1 — DAE/OBJ Migration (SketchUp Workflow) 🎯 NEXT

**Goal**: Replace broken SKP pipeline with Blender native Collada/OBJ import; reject `.skp` with export instructions

**Independent Test**: `curl -F file=@sample.dae /upload` → `Ready`, `sourceFormat: "dae"`; `curl -F file=@sample.skp /upload` → `415` with Collada hint

### Converter

- [x] T088 [P] Create `app/converter/mesh_to_glb.py` — Blender batch: `import_scene.dae` / `import_scene.obj` → glTF binary GLB
- [x] T089 [P] Create `app/converter/mesh_pipeline.py` — orchestrate DAE/OBJ write → mesh_to_glb → common post-process
- [x] T090 [US1] Update `app/converter/converter_service.py` — dispatch `ifc`|`dae`|`obj`; remove SKP branch
- [x] T091 [US1] Delete `app/converter/skp_to_glb.py` and `app/converter/skp_pipeline.py`
- [x] T092 [P] Rename `SKP_CONVERSION_TIMEOUT_S` → `MESH_CONVERSION_TIMEOUT_S` in `app/converter/Dockerfile`, `app/docker-compose.yml`, `app/.env.example`

### Backend

- [x] T093 [US1] Update `app/backend/Domain/SourceFormat.cs` — replace `Skp` with `Dae` and `Obj`
- [x] T094 [US1] Update `app/backend/Domain/Project.cs` and `app/backend/Infrastructure/LocalFileStorage.cs` — `original.dae`, `original.obj` paths
- [x] T095 [US1] Update `POST /upload` in `app/backend/Program.cs` — accept `.dae`/`.obj`; validate COLLADA/OBJ signatures; reject `.skp` with SketchUp export message (FR-001b)
- [x] T096 [US1] Update `app/backend/Infrastructure/HttpModelConverter.cs` — pass `sourceFormat` `dae`|`obj` to converter sidecar

### Frontend

- [x] T097 [P] [US1] Update `app/frontend/src/pages/HomePage.tsx` — `accept=".ifc,.dae,.obj"`; prominent SketchUp export instructions (FR-001a); remove `.skp` references

### Tests

- [x] T098 [P] Add minimal Collada fixture `app/tests/backend/Integration/Fixtures/sample.dae`
- [x] T099 [P] [US1] Create `app/tests/backend/Integration/DaeUploadConversionTests.cs` — DAE upload → Ready, `original.dae` + GLB/USDZ/WebP on disk
- [x] T100 [US1] Replace `app/tests/backend/Integration/SkpUploadConversionTests.cs` — assert `.skp` upload returns 415 with Collada export hint
- [x] T101 [P] [US1] Create `app/converter/test_mesh_to_glb.py` — DAE fixture → non-empty GLB via Blender
- [x] T102 [P] Delete `app/converter/test_skp_to_glb.py`

**Checkpoint**: IFC + DAE upload paths produce shareable links; SKP rejected

---

## Phase 11: Polish & Validation

**Purpose**: Docs, full quickstart, manual AR for DAE workflow

- [x] T103 [P] Update `app/README.md` — DAE/OBJ SketchUp workflow, no direct SKP, `MESH_CONVERSION_TIMEOUT_S`
- [x] T104 [P] Update `app/converter/converter_service.py` docstring to match `specs/001-ifc-mvp-platform/contracts/openapi.md` (dae|obj)
- [x] T105 Run `dotnet test app/tests/backend/Integration/` — IFC + DAE + SKP rejection + file serving pass
- [x] T106 [P] Run `cd app/frontend && npm test` — SharePage + admin boundary pass
- [x] T107 [P] Run `cd app/converter && python -m pytest test_*.py -v`
- [ ] T108 Run quickstart automated scenarios §0–§5 from `specs/001-ifc-mvp-platform/quickstart.md`
- [ ] T109 Complete manual AR checklist §8 (IFC + DAE) on Android + iPhone over HTTPS
- [ ] T110 [P] Grep `app/` for `skp`/`SKP`/`io_sketchup` — remove stale references

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phases 1–9 (IFC + WebP + abstractions) ✅ COMPLETE
    ↓
Phase 10 (DAE/OBJ migration) — BLOCKS production SketchUp workflow
    ↓
Phase 11 (Polish + validation)
```

### User Story Dependencies

- **US1 (DAE/OBJ)**: Phase 10 — extends upload; HomePage changes in T097
- **US2**: No code changes expected; re-validate DAE uploads render in viewer (T109)
- **US3**: No code changes; re-validate AR with DAE-sourced models (T109)

### Within Phase 10

```text
T088 mesh_to_glb.py ─┐
T089 mesh_pipeline.py ┼→ T090 converter_service.py → T091 delete SKP files
T092 env rename [P]   ┘
         ↓
T093–T096 backend (sequential on Program.cs after T093)
         ↓
T097 frontend [P] (parallel with T099–T101 after T095)
T098 fixture [P] → T099–T101 tests
```

### Parallel Opportunities

**Phase 10** (after T088+T089 exist):
```bash
# Parallel:
T088 mesh_to_glb.py
T089 mesh_pipeline.py
T092 MESH_CONVERSION_TIMEOUT_S rename
T098 sample.dae fixture

# Then:
T090 converter_service.py
T093 SourceFormat.cs
T097 HomePage.tsx (after T095 for error message copy alignment)
T099–T101 tests
```

---

## Parallel Example: Phase 10

```bash
# Launch together after Phase 9 complete:
Task T088: "Create app/converter/mesh_to_glb.py"
Task T089: "Create app/converter/mesh_pipeline.py"
Task T098: "Add app/tests/backend/Integration/Fixtures/sample.dae"

# After T090, launch together:
Task T097: "Update app/frontend/src/pages/HomePage.tsx"
Task T101: "Create app/converter/test_mesh_to_glb.py"
```

---

## Implementation Strategy

### Current state

- Phases 1–9 complete: IFC upload, local storage, WebP thumbnail, AR attrs, service interfaces.
- Phase 7 SKP code exists but **broken in production** (no `io_sketchup` in stock Blender).

### Next MVP increment (Phase 10 only)

1. T088–T091: Converter mesh pipeline; remove SKP dead code
2. T093–T096: Backend format enum + validation + SKP rejection
3. T097: Frontend accept + SketchUp guide
4. T098–T102: DAE integration tests + SKP rejection test
5. **Validate**: quickstart §2 DAE upload; §2 failure case `.skp` → 415

### Full validation (Phase 11)

1. T105–T108 automated suites + quickstart
2. T109 manual AR (IFC + DAE) over HTTPS

### Suggested scope for next PR

**Phase 10 tasks T088–T102** — DAE/OBJ SketchUp workflow end-to-end.

---

## Notes

- **Total tasks**: 110 (105 complete + 3 remaining in Phase 11 manual validation)
- **Remaining**: T108 quickstart E2E, T109 manual AR, T110 grep cleanup (optional)
- **Per story (remaining)**: US1 +15, US2 +0 (re-test), US3 +0 (re-test AR)
- USDZ failure must fail entire upload (no GLB-only fallback)
- Never use 3xx redirects on `/files/` routes
- `PUBLIC_BASE_URL` must be HTTPS for device AR tests
- Mesh timeout default 180s (`MESH_CONVERSION_TIMEOUT_S`); IFC 120s
- Blender Collada/OBJ import validated with `sample.dae` fixture in T101
- Do **not** install SketchUp Importer addon — stock Blender only (R-21)
