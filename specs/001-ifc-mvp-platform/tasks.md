# Tasks: Arch3DAR — IFC/SKP → Web 3D + AR MVP

**Input**: Design documents from `specs/001-ifc-mvp-platform/`

**Prerequisites**: plan.md, spec.md (clarifications 2026-06-10), research.md (R-11…R-20), data-model.md, contracts/openapi.md, quickstart.md

**Tests**: Included — SC-007 and quickstart §8 require automated E2E coverage for upload, conversion, and file serving.

**Organization**: Phases 1–6 delivered IFC correction (complete). Phases 7–9 extend US1 with SKP + WebP thumbnail. US2/US3 updated where asset URLs change.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to spec user story (US1, US2, US3)
- Every task includes an exact file path

## User Story Mapping

| Story | Priority | Goal | Independent Test |
|---|---|---|---|
| **US1** | P1 | Upload `.ifc` or `.skp` → GLB + USDZ + thumbnail → public link + QR | `POST /upload` → `Ready`; `/data/projects/{id}/` has all artifacts |
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

## Phase 4: User Story 2 — File Serving + Share API (Complete ✅ — WebP update in Phase 8)

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

## Phase 7: User Story 1 — SKP Support (SpecDrive Phase B) ✅

**Goal**: Upload `.skp` → Blender headless SKP→GLB → common pipeline → link público

**Independent Test**: `curl -F file=@sample.skp /upload` → `Ready`, `sourceFormat: "skp"`, SKP materials visible in viewer

### Implementation

- [x] T054 [P] Add Blender 4.2 LTS and headless deps (`libgl1`, `libxi6`) to `app/converter/Dockerfile`
- [x] T055 [P] Create `app/converter/skp_to_glb.py` — Blender batch: import SKP, export glTF binary
- [x] T056 [P] Extract IFC steps into `app/converter/ifc_pipeline.py` from `app/converter/converter_service.py`
- [x] T057 [US1] Update `app/converter/converter_service.py` — accept `sourceFormat` form field; dispatch IFC vs SKP pipeline
- [x] T058 [US1] Add `SourceFormat` enum in `app/backend/Domain/SourceFormat.cs` and column on `Project` in `app/backend/Domain/Project.cs`
- [x] T059 [US1] Add migration `app/backend/Migrations/20260610130000_AddSourceFormat.cs` — `SourceFormat` column
- [x] T060 [US1] Update `POST /upload` in `app/backend/Program.cs` — accept `.skp`, validate ZIP/SketchUp signature, set `SourceFormat`
- [x] T061 [US1] Update `app/backend/Infrastructure/HttpModelConverter.cs` — pass `sourceFormat` to converter sidecar
- [x] T062 [P] [US1] Update `app/frontend/src/pages/HomePage.tsx` — `accept=".ifc,.skp"`, show `sourceFormat` on success
- [x] T063 [P] [US1] Add `SKP_CONVERSION_TIMEOUT_S` and `MAX_UPLOAD_MB` in `app/.env.example`

### Tests

- [x] T064 [P] [US1] Add minimal SKP fixture generation in `app/tests/backend/Integration/SkpUploadConversionTests.cs`
- [x] T065 [US1] Create `app/tests/backend/Integration/SkpUploadConversionTests.cs` — SKP upload → Ready, `original.skp` + GLB/USDZ on disk
- [x] T066 [P] [US1] Create `app/converter/test_skp_to_glb.py` — smoke test SKP fixture → non-empty GLB

**Checkpoint**: Both IFC and SKP upload paths produce shareable links

---

## Phase 8: Thumbnail WebP Migration (SpecDrive Phase C) ✅

**Goal**: Replace `thumbnail.png` with `thumbnail.webp` via Blender render (both formats)

**Independent Test**: `curl -sI /files/{id}/thumbnail.webp` → 200, `image/webp`

### Implementation

- [x] T067 [P] Create `app/converter/render_thumbnail.py` — Blender headless: import GLB, render → WebP 512px
- [x] T068 [US1] Update `app/converter/converter_service.py` — call `render_thumbnail.py` after GLB normalize (IFC + SKP paths)
- [x] T069 [P] [US2] Add `.webp` → `image/webp` in `app/backend/Infrastructure/ModelContentTypeMiddleware.cs`
- [x] T070 [US2] Replace `GET /files/{projectId}/thumbnail.png` with `thumbnail.webp` in `app/backend/Program.cs`
- [x] T071 [US2] Update `GET /share/{token}` thumbnail URL to `.webp` in `app/backend/Program.cs`
- [x] T072 [P] [US2] Update `app/frontend/src/pages/SharePage.tsx` poster to use WebP `thumbnailUrl`
- [x] T073 [P] Update default `ThumbnailFileName` to `thumbnail.webp` in `app/backend/Domain/Project.cs`

### Tests

- [x] T074 [P] [US2] Update `app/tests/backend/Integration/FileServingTests.cs` — assert `image/webp` Content-Type
- [x] T075 [P] [US1] Update `app/tests/backend/Integration/UploadConversionTests.cs` — assert `thumbnail.webp` exists on disk
- [x] T076 [P] Create `app/converter/test_render_thumbnail.py` — GLB fixture → non-empty WebP

**Checkpoint**: All new uploads produce WebP thumbnails; PNG route removed

---

## Phase 9: Service Abstractions + Polish

**Purpose**: FR-010 interfaces, docs, full quickstart validation

### Service interfaces (FR-010)

- [x] T077 [P] Create `app/backend/Services/IModelConversionService.cs` — abstract conversion contract
- [x] T078 [P] Create `app/backend/Services/IFileStorageService.cs` wrapping `LocalFileStorage` operations
- [x] T079 Register `IModelConversionService` → `HttpModelConverter` adapter in `app/backend/Program.cs`

### Cross-cutting

- [x] T080 [P] Update `app/README.md` — SKP support, Blender in converter, WebP thumbnail, env vars
- [x] T081 [P] Update `app/converter/converter_service.py` OpenAPI docstring to match `specs/001-ifc-mvp-platform/contracts/openapi.md`
- [x] T082 Run `dotnet test app/tests/backend/Integration/` — all IFC + SKP + file serving tests pass
- [x] T083 [P] Run `cd app/frontend && npm test` — SharePage + ModelViewerAr tests pass
- [x] T084 [P] Run `cd app/converter && python -m pytest test_*.py -v`
- [ ] T085 Run quickstart automated scenarios §0–§4 from `specs/001-ifc-mvp-platform/quickstart.md`
- [ ] T086 Complete manual AR checklist §7 (IFC + SKP) on Android + iPhone over HTTPS
- [x] T087 [P] Grep `app/` for `thumbnail.png` — remove stale references

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phases 1–6 (IFC correction) ✅ COMPLETE
    ↓
Phase 7 (SKP) — requires T054 Blender in Dockerfile before T055–T057
    ↓
Phase 8 (WebP) — can start T067 in parallel with Phase 7 converter work; T068 integrates after T057
    ↓
Phase 9 (Polish) — after Phases 7 + 8
```

### User Story Dependencies

- **US1 (SKP)**: Phase 7 extends upload; independent of US2/US3 frontend except HomePage accept attr
- **US2 (WebP)**: Phase 8 updates poster URL — US3 AR unchanged (USDZ path same)
- **US3**: Already complete; re-validate after SKP uploads in Phase 9 §7

### Parallel Opportunities

**Phase 7** (after T054):
```bash
# Parallel:
T055 skp_to_glb.py
T056 ifc_pipeline.py
T064 sample.skp fixture

# Then sequential:
T057 converter_service.py router
T058–T061 backend + migration
T065–T066 tests
```

**Phase 8** (after T067):
```bash
# Parallel:
T069 ModelContentTypeMiddleware.cs
T072 SharePage.tsx
T074–T076 tests
```

---

## Parallel Example: Phase 7 SKP

```bash
# After T054 (Blender in Dockerfile), launch together:
Task T055: "Create app/converter/skp_to_glb.py"
Task T056: "Extract app/converter/ifc_pipeline.py"
Task T064: "Add app/tests/backend/Integration/Fixtures/sample.skp"
```

---

## Implementation Strategy

### Current state

Phases 1–6 complete — IFC upload, local storage, direct file serving, web viewer, AR attrs all working with `thumbnail.png`.

### Next MVP increment (Phase 7 only)

1. T054–T057: Blender + SKP pipeline in converter
2. T058–T061: Backend + frontend accept SKP
3. T064–T066: SKP integration tests
4. **Validate**: quickstart §2 SKP upload

### Full SpecDrive MVP (Phases 7 + 8 + 9)

1. Phase 7 → SKP works end-to-end
2. Phase 8 → WebP thumbnails
3. Phase 9 → interfaces, docs, full quickstart + manual AR for both formats

### Suggested scope for next PR

**Phase 7 tasks T054–T066** — SKP upload without waiting for WebP migration (PNG thumbnail acceptable as interim).

---

## Notes

- **Total tasks**: 87 (85 complete + 2 remaining: T085 quickstart E2E, T086 manual AR)
- **Remaining by phase**: Polish 2 (manual validation)
- **Per story (remaining)**: US1 +12, US2 +8, US3 +0 (re-test only)
- USDZ failure must fail entire upload (no GLB-only fallback)
- Never use 3xx redirects on `/files/` routes
- `PUBLIC_BASE_URL` must be HTTPS for device AR tests
- SKP timeout default 180s (`SKP_CONVERSION_TIMEOUT_S`); IFC 120s
- Blender SKP import on Linux must be validated with real fixture in T066
