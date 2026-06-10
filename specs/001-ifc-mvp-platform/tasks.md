---
description: "Task list for Arch3DAR MVP — IFC-to-AR 3D sharing SaaS"
---

# Tasks: Arch3DAR — IFC-to-AR 3D Sharing MVP

**Input**: Design documents from `/specs/001-ifc-mvp-platform/`
- `plan.md` (tech stack + structure)
- `spec.md` (5 user stories: US1 P1, US2 P1, US3 P1, US4 P2, US5 P3 — 33 functional requirements)
- `research.md` (10 decisions: ASP.NET Core 9, MediatR, Serilog, QRCoder, MinIO, `<model-viewer>`, IfcOpenShell, Postgres `FOR UPDATE SKIP LOCKED`, ASP.NET Identity cookies, xUnit+Testcontainers+Playwright)
- `data-model.md` (`Project`, `ShareLink`, ASP.NET Identity)
- `contracts/openapi.md` (8 HTTP endpoints + Python converter HTTP)
- `quickstart.md` (10 runnable end-to-end scenarios)

**Tests**: Required by `.specify/memory/constitution.md` §IV. Test tasks are interleaved with implementation tasks per user story.

**Organization**: Tasks are grouped by user story so each is independently implementable, testable, and deployable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User-story label (`[US1]…[US5]`). Setup/Foundational/Polish phases have no story label.
- Each task includes an exact file path.

## Path Conventions

Web application layout (per `plan.md` and the constitution's `app/{backend,frontend,converter,tests}/` mandate):

- Backend: `app/backend/{Domain,Application,Infrastructure,Api}/`
- Frontend: `app/frontend/src/{pages,components,api,auth}/`
- Converter: `app/converter/`
- Backend tests: `app/tests/backend/{Unit,Integration,Contract}/`
- Frontend tests: `app/tests/frontend/{Unit,E2E}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency wiring, repo hygiene. Everything here is independent of any user story.

- [X] T001 Create `app/backend/{Domain,Application/Abstractions,Application/Projects/Commands,Application/Projects/Queries,Application/Projects/Validators,Application/Projects/Dtos,Application/Sharing/Dtos,Infrastructure,Api/Endpoints,Migrations}` folder skeleton in `app/backend/`
- [X] T002 [P] Add NuGet packages to `app/backend/Backend.csproj`: `MediatR` 14.x, `Microsoft.EntityFrameworkCore.Design` 9.x, `Npgsql.EntityFrameworkCore.PostgreSQL` 9.x, `Microsoft.AspNetCore.Identity.EntityFrameworkCore` 9.x, `FluentValidation.AspNetCore` 11.x, `QRCoder` 1.8.x, `Serilog.AspNetCore` 9.x, `Minio` 6.0.x, `Swashbuckle.AspNetCore` 7.x, `xunit` 2.x (test project)
- [X] T003 [P] Add dev dependencies to `app/frontend/package.json`: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@playwright/test`, `jsdom`
- [X] T004 [P] Add `app/converter/requirements.txt` entries: `fastapi`, `uvicorn[standard]`, `minio>=7.0.0`, `psycopg[binary]>=3.1.0`, `ifcopenshell==0.8.0`, `Pillow`
- [X] T005 [P] Add `app/backend/.gitignore` patterns for `bin/`, `obj/`, `*.user`; add top-level `app/.gitignore` entries for `app/backend/obj/`, `app/converter/__pycache__/`, `.env`, `app/backend/.env`
- [X] T006 [P] Delete `app/converter/__pycache__/` (stale Python 3.14 bytecode) and add it to `app/converter/.gitignore`
- [X] T007 [P] Add `app/.env.example` keys: `PUBLIC_BASE_URL`, `MAX_IFC_MB=100`, `CONVERSION_TIMEOUT_S=300`, `ASPNETCORE_SIGNING_KEY` (or use Identity's default), `CORS_ALLOWED_ORIGINS`
- [X] T008 [P] Configure Serilog in `app/backend/Api/Program.cs` with console + structured JSON sinks, `LogContext` push for `CorrelationId`, and `UseSerilogRequestLogging()`
- [X] T009 [P] Set up ESLint + Prettier in `app/frontend/` with `tsconfig.json` `strict: true` and React 18 JSX runtime
- [X] T010 [P] Pin `IfcConvert` Linux64 binary URL and sha256 in `app/converter/Dockerfile`; remove the silent `|| echo "WARNING"` fallback so a failed download is a hard build failure
- [X] T011 [P] Add `app/backend/Dockerfile` healthcheck (`HEALTHCHECK CMD curl --fail http://localhost:5000/health || exit 1`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be implemented. After this phase, all five user stories can start in parallel.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T012 Create `Project` entity with state machine in `app/backend/Domain/Project.cs`: `Id (Guid)`, `OwnerId (Guid)`, `Name`, `Description?`, `ClientLabel?`, `Status`, `ErrorMessage?`, `IfcObjectKey?`, `GlbObjectKey?`, `ThumbnailObjectKey?`, `IfcSizeBytes?`, `ConversionStartedAt?`, `ConversionDurationMs?`, `CreatedAt`, `UpdatedAt`, `PublishedAt?`; add `TransitionTo(ProjectStatus next)` method that validates the diagram in `data-model.md §State machine` and throws `InvalidStateTransitionException` on illegal transitions
- [X] T013 [P] Create `ProjectStatus` enum in `app/backend/Domain/ProjectStatus.cs` with values `UploadReceived, Processing, ReadyToPublish, Published, Failed` (spec FR-006)
- [X] T014 [P] Create `ShareLink` entity in `app/backend/Domain/ShareLink.cs`: `Id (Guid)`, `ProjectId (Guid)`, `PublicToken (Guid)`, `QrCodeObjectKey?`, `CreatedAt`; unique index on `ProjectId` and on `PublicToken`
- [X] T015 [P] Create `IModelConverter` interface in `app/backend/Application/Abstractions/IModelConverter.cs` with `Task<ConversionResult> ConvertAsync(Guid projectId, CancellationToken ct)`; `ConversionResult` record in same file
- [X] T016 [P] Create `CorrelationIdMiddleware` in `app/backend/Infrastructure/CorrelationIdMiddleware.cs` that reads `X-Correlation-Id` (or generates a Guid) and pushes it into `Serilog.Context.LogContext`
- [X] T017 [P] Create `MinioService` in `app/backend/Infrastructure/MinioService.cs` with `EnsureBucketsAsync`, `UploadStreamAsync(bucket, key, stream, contentType)`, `GetPresignedUrlAsync(bucket, key, ttl)` (use the `Minio` NuGet 6.0.x; presigned-URL TTL = 10 min)
- [X] T018 [P] Create `QrCodeService` in `app/backend/Infrastructure/QrCodeService.cs` with `byte[] GeneratePng(string url)` using `PngByteQRCodeHelper.GetQRCode(url, ECCLevel.Q, pixelsPerModule: 20)`; returns PNG bytes
- [X] T019 [P] Create `AppDbContext` in `app/backend/Infrastructure/AppDbContext.cs` with `DbSet<Project>`, `DbSet<ShareLink>`, `IdentityDbContext<IdentityUser, IdentityRole, Guid>` base, global query filter `OwnerId == currentUserId`, fluent config matching `data-model.md §Indexes`
- [X] T020 [P] Create EF migration `00000000000000_Initial.cs` (`dotnet ef migrations add Initial`) creating `projects`, `share_links`, all indexes, and FKs
- [X] T021 [P] Add ASP.NET Identity registration in `app/backend/Api/Program.cs`: `AddIdentity<IdentityUser, IdentityRole>().AddEntityFrameworkStores<AppDbContext>().AddDefaultTokenProviders()`; cookie auth defaults; `[Authorize]` on `/api/projects/*`; `[AllowAnonymous]` on `/api/share/*` and `/health`; replace `EnsureCreated()` with `Database.Migrate()` on startup
- [X] T022 [P] Register MediatR in `app/backend/Api/Program.cs` with `cfg.RegisterServicesFromAssembly(typeof(Program).Assembly)`; register `FluentValidation` and auto-validate; register `HttpModelConverter` as the `IModelConverter` implementation pointed at `http://converter:8080`
- [X] T023 [P] Add ProblemDetails middleware in `app/backend/Api/Program.cs` returning `application/problem+json` with `correlationId` field; map `InvalidStateTransitionException` → 409, `ValidationException` → 400 with `errors` object, default unhandled → 500 with no stack trace
- [X] T024 [P] Create `app/backend/Api/Endpoints/AuthEndpoints.cs` with `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`; responses per `contracts/openapi.md §POST /auth/register`
- [X] T025 [P] Create test project `app/tests/backend/Backend.Tests.csproj` with xUnit + FluentAssertions + Testcontainers + `Microsoft.AspNetCore.Mvc.Testing`; reference `app/backend/Backend.csproj`
- [X] T026 [P] Create test project `app/tests/frontend/` with `vitest.config.ts`, `playwright.config.ts`, and a `setupTests.ts` registering `@testing-library/jest-dom`
- [X] T027 [P] Add fixture `app/tests/backend/Integration/Fixtures/sample.ifc` (200 KB sample IFC2x3 file, committed binary)
- [X] T028 [P] Create `app/tests/backend/Integration/AppFactory.cs` extending `WebApplicationFactory<Program>` with `Testcontainers.PostgreSql`, `Testcontainers.Minio`, and a one-shot `Testcontainers.GenericContainer` running the `app/converter` image (binds to a `http://converter:8080` test endpoint)
- [X] T029 [P] Create `app/converter/converter_service.py` exposing `POST /convert` (per `contracts/openapi.md §Python Converter HTTP Contract`) and a `claim_pending_projects` loop using `SELECT … FOR UPDATE SKIP LOCKED`; thin `app/converter/converter.py` shim that re-exports the new module
- [X] T030 [P] Update `app/docker-compose.yml` to drop the dev-only `nginx` service and ensure `depends_on: service_healthy` chains for `backend → postgres + minio` and `converter → minio + postgres`; pin all image tags to specific versions

**Checkpoint**: Foundation ready — every user story can now start in parallel.

---

## Phase 3: User Story 1 — Architect publishes a model and shares a public link (Priority: P1) 🎯 MVP

**Goal**: An architect creates a project, uploads an `.ifc`, the system stores it, the converter runs and produces a GLB + thumbnail, and the architect publishes and receives a public URL + QR code.

**Independent Test**: Create a project, upload a valid IFC, watch status reach `ready-to-publish`, call `POST /api/projects/{id}/publish`, confirm response includes a `publicUrl` and a `qrCodeUrl`; calling publish again returns the same token (idempotent).

### Tests for User Story 1 ⚠️

- [X] T031 [P] [US1] Unit test `Project.TransitionTo` in `app/tests/backend/Unit/ProjectStateTransitionTests.cs`: 6 valid transitions, 6 invalid transitions, terminal `Published` rejects further moves
- [X] T032 [P] [US1] Unit test publish idempotency in `app/tests/backend/Unit/PublishProjectHandlerTests.cs`: second `PublishProject` call returns the same `publicToken` and does not create a second `ShareLink` row
- [X] T033 [P] [US1] Integration test upload+convert+publish in `app/tests/backend/Integration/ProjectLifecycleTests.cs`: upload a `sample.ifc`, poll until `ready-to-publish`, publish, assert `publicUrl` matches `${PUBLIC_BASE_URL}/s/{guid}`, assert presigned QR URL returns a 200 with `Content-Type: image/png`
- [X] T034 [P] [US1] Integration test upload validation in `app/tests/backend/Integration/UploadValidationTests.cs`: non-IFC file → 415 + ProblemDetails; oversize file → 413; missing name → 400 with `errors.name`
- [X] T035 [P] [US1] Integration test conversion failure in `app/tests/backend/Integration/ConversionFailureTests.cs`: a corrupted IFC in the test project makes the converter return 500; project transitions to `Failed` with a user-readable `ErrorMessage`; `POST /publish` returns 409
- [X] T036 [P] [US1] Contract test `POST /api/projects` response shape in `app/tests/backend/Contract/CreateProjectContractTests.cs`: snapshot test against `ProjectDto` schema in `data-model.md §ProjectDto`

### Implementation for User Story 1

- [X] T037 [P] [US1] Create `CreateProjectHandler` in `app/backend/Application/Projects/Commands/CreateProjectHandler.cs`: accepts `CreateProjectCommand(name, description?, clientLabel?, IFormFile file)`, streams the file to MinIO under `ifc-files/projects/{id}/source.ifc`, persists the `Project` row, returns `ProjectDto`
- [X] T038 [P] [US1] Create `CreateProjectValidator` in `app/backend/Application/Projects/Validators/CreateProjectValidator.cs` with FluentValidation rules for FR-001/003/004/033 (name 1–200, description ≤ 2000, clientLabel ≤ 200, file present, file size, file signature, file extension)
- [X] T039 [P] [US1] Create `PublishProjectHandler` in `app/backend/Application/Projects/Commands/PublishProjectHandler.cs`: looks up existing `ShareLink` by `ProjectId` (idempotent); on miss, creates one with `PublicToken = Guid.NewGuid()`, calls `QrCodeService.GeneratePng(publicUrl)`, uploads to `qrcodes/projects/{projectId}/qr.png`, transitions project to `Published`; returns `PublishResultDto`
- [X] T040 [P] [US1] Create `PublishProjectValidator` in `app/backend/Application/Projects/Validators/PublishProjectValidator.cs`: asserts `Status == ReadyToPublish`
- [X] T041 [P] [US1] Create `GetProjectHandler` in `app/backend/Application/Projects/Queries/GetProjectHandler.cs`: returns `ProjectDto` for the given `id`; throws `NotFoundException` if missing OR not owned by current user (no enumeration leak; SC-006)
- [X] T042 [P] [US1] Create `ListProjectsHandler` in `app/backend/Application/Projects/Queries/ListProjectsHandler.cs`: tenant-scoped, paginated by `createdAt + id` cursor, returns `ProjectSummaryDto[]`
- [X] T043 [US1] Create `ProjectsEndpoints` in `app/backend/Api/Endpoints/ProjectsEndpoints.cs` mapping `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{id}`, `POST /api/projects/{id}/publish` per `contracts/openapi.md` (depends on T037, T039, T041, T042)
- [X] T044 [US1] Implement `HttpModelConverter` in `app/backend/Infrastructure/HttpModelConverter.cs`: `IModelConverter.ConvertAsync` POSTs `{ "projectId": "..." }` to `${CONVERTER_URL}/convert`; maps non-2xx to `ConversionException(reason)` (depends on T022)
- [X] T045 [US1] Stream upload (no in-memory buffering) in `CreateProjectHandler`: use `IFormFile.OpenReadStream()` and pipe directly into `MinioService.UploadStreamAsync`; only create the project row after the MinIO upload completes (atomic; fixes Risk 4 from research §R-04)

**Checkpoint**: US1 is fully functional. You can upload an IFC, watch it convert, and get a public URL + QR.

---

## Phase 4: User Story 2 — Client opens the public link and views the 3D model (Priority: P1)

**Goal**: An unauthenticated client opens a public URL, sees a thumbnail while the GLB loads, then interacts with the 3D model (orbit / zoom / pan / fullscreen). Status of the underlying project (processing / not-found) is shown gracefully.

**Independent Test**: Hit `GET /api/share/{token}` (no auth) in incognito, then load the public page in a real browser. The `<model-viewer>` element renders; orbit/zoom/pan/fullscreen all work; thumbnail is visible before the GLB; "not found" / "still processing" branches render correctly.

### Tests for User Story 2 ⚠️

- [X] T046 [P] [US2] Integration test public endpoint in `app/tests/backend/Integration/PublicShareEndpointTests.cs`: known token returns `PublicShareDto` with `glbUrl` + `thumbnailUrl` (presigned); unknown token returns 404; project in `Processing` returns 404 (no preview yet)
- [X] T047 [P] [US2] Contract test `PublicShareDto` in `app/tests/backend/Contract/PublicShareContractTests.cs`: response contains ONLY `name`, `clientLabel`, `status`, `glbUrl`, `thumbnailUrl` — assert zero leakage of `id`, `ownerId`, `errorMessage`, `createdAt`, `updatedAt` (FR-025)
- [X] T048 [P] [US2] Frontend unit test `<SharePage>` in `app/tests/frontend/Unit/SharePage.test.tsx`: renders `<model-viewer>` with `src`, `poster`, `ar`, `ar-modes="webxr scene-viewer quick-look"`, `camera-controls`, `autoplay`; renders thumbnail before GLB loads; renders "not found" on 404; renders "processing" on `status === 'processing'`
- [X] T049 [P] [US2] Frontend unit test `<ModelViewer>` wrapper in `app/tests/frontend/Unit/ModelViewer.test.tsx`: forwards props, hides AR button when `isArCapable === false` (FR-019)
- [X] T050 [P] [US2] E2E test public page in `app/tests/frontend/E2E/public-page.spec.ts` (Playwright): boot the full docker-compose, create+upload+publish a sample project, open `/s/{token}` in a headless Chromium with a UA-string spoofed Android, assert `<model-viewer>` element exists and has `ar` attribute, take a screenshot

### Implementation for User Story 2

- [X] T051 [P] [US2] Create `PublicShareHandler` in `app/backend/Application/Sharing/PublicShareHandler.cs`: looks up `ShareLink` by `PublicToken`; returns 404 if missing or if project is not in `Published`; otherwise returns `PublicShareDto` with presigned `glbUrl` and `thumbnailUrl`
- [X] T052 [P] [US2] Create `PublicShareEndpoints` in `app/backend/Api/Endpoints/PublicShareEndpoints.cs` with `GET /api/share/{token}` (anonymous, per `contracts/openapi.md §GET /api/share/{token}`)
- [X] T053 [P] [US2] Create `<ModelViewer>` component in `app/frontend/src/components/ModelViewer.tsx`: a typed React wrapper for `<model-viewer>` accepting `glbUrl`, `thumbnailUrl`, `isArCapable` props; renders the `ar-modes="webxr scene-viewer quick-look"` attributes; hides the AR button via CSS when `!isArCapable`
- [X] T054 [P] [US2] Create `<StatusBadge>` component in `app/frontend/src/components/StatusBadge.tsx`: maps `ProjectStatus` to a colour label using kebab-case spec names (`upload-received`, `processing`, `ready-to-publish`, `published`, `failed`)
- [X] T055 [US2] Rewrite `<SharePage>` in `app/frontend/src/pages/SharePage.tsx`: fetch `/api/share/{token}`, render `<ModelViewer>` with the returned URLs, show `<StatusBadge>` while loading, show "still processing" if backend returns 404 due to non-`Published` status (try fetching project state via a secondary endpoint if needed), show "not found" page on 404; remove the OG `og:title` "BIM Project" fallback (depends on T051, T053)
- [X] T056 [US2] Update `app/frontend/src/App.tsx` routes: `/s/:token` → `SharePage`; add a `*` route → `<NotFoundPage>` (US-2 AC-5)
- [X] T057 [US2] Update `app/frontend/src/index.html`: change `<title>` from "Arch3DAR - BIM 3D Viewer" to "Arch3DAR" (FR-031)
- [X] T058 [P] [US2] Update `app/frontend/src/api/client.ts`: add `getPublicShare(token)` (no auth header); ensure `X-Correlation-Id` is attached to every request (generate one client-side if absent; FR-027)
- [X] T059 [P] [US2] Update `app/frontend/vite.config.ts` and `app/frontend/nginx.conf`: ensure `/s/:token` is a frontend route (not proxied to backend); `/api/share/:token` is proxied to backend

**Checkpoint**: A client can open a shared link with no auth and view the 3D model end-to-end.

---

## Phase 5: User Story 3 — Client places the model in their real environment via AR (Priority: P1)

**Goal**: On a mobile device, the client taps an "Open in AR" button on the public page and the system launches the device's native AR experience (Scene Viewer on Android, Quick Look on iOS) at real-world scale. On non-AR devices, the button is hidden or disabled and the 3D viewer remains functional.

**Independent Test**: On Android Chrome with ARCore, tap AR → Scene Viewer launches. On iOS Safari, the AR button hands off to Quick Look. On desktop Chrome, no AR button is shown.

### Tests for User Story 3 ⚠️

- [X] T060 [P] [US3] E2E test AR handoff in `app/tests/frontend/E2E/ar-handoff.spec.ts` (Playwright): boot full stack, publish a project, open `/s/{token}` with an Android UA spoof, assert `<model-viewer ar>` attribute present and `ar-modes` contains `scene-viewer` and `quick-look`
- [X] T061 [P] [US3] Frontend unit test AR capability detection in `app/tests/frontend/Unit/ModelViewer.test.tsx`: when `navigator.userAgent` contains "Android" → `isArCapable = true`; when "iPhone" / "iPad" → `isArCapable = true`; when "Macintosh" with `!X…` UA → `isArCapable = false`; default `false` for unknown UAs (FR-019 graceful degradation)

### Implementation for User Story 3

- [X] T062 [US3] Implement `useArCapability` hook in `app/frontend/src/auth/useArCapability.ts`: returns `true` on Android or iOS UA, `false` otherwise; SSR-safe (defaults to `false` until `useEffect`)
- [X] T063 [US3] Wire AR capability into `<ModelViewer>` in `app/frontend/src/components/ModelViewer.tsx`: if `!isArCapable` hide the inner model-viewer element's AR button by setting `ar="false"` (or omitting the `ar` attribute); if `isArCapable` render with the full `ar-modes="webxr scene-viewer quick-look"` (depends on T062)
- [X] T064 [US3] Add an HTTPS-required banner in `<SharePage>` in `app/frontend/src/pages/SharePage.tsx`: if `window.location.protocol === 'http:'` and `isArCapable`, render a non-blocking notice ("AR requires HTTPS — use a secure URL to launch AR")
- [X] T065 [P] [US3] (Optional, non-MVP) Add `<a rel="ar" href="…usdz…">` fallback in `<SharePage>` for iOS Quick Look when a USDZ companion is available; skip if absent (post-MVP USDZ generation is out of scope per `research.md §R-06`)

**Checkpoint**: AR handoff works on Android; iOS handoff is wired (USDZ companion out of scope for MVP); no-AR devices degrade gracefully.

---

## Phase 6: User Story 4 — Architect manages projects from a dashboard (Priority: P2)

**Goal**: Authenticated users can sign in to a dashboard that lists their projects, create new ones, upload a file with progress, see status, open a project detail with thumbnail + status + generated assets, and trigger publishing from a share dialog showing the QR code inline + a copy-to-clipboard button.

**Independent Test**: Log in, see the dashboard list, create + upload a new project, see the status badge transition from `upload-received` → `processing` → `ready-to-publish`, open the detail, click publish, see a share dialog with the QR code image and the public URL, copy the URL to clipboard.

### Tests for User Story 4 ⚠️

- [X] T066 [P] [US4] Frontend unit test `<UploadPage>` in `app/tests/frontend/Unit/UploadPage.test.tsx`: renders `name`, `description`, `clientLabel` fields; rejects non-`.ifc` files client-side; shows progress indicator while uploading; switches to "processing" state on 201 response; shows server error on 4xx
- [X] T067 [P] [US4] Frontend unit test `<DashboardPage>` (list) in `app/tests/frontend/Unit/DashboardPage.test.tsx`: renders project list with name, date, status badge, thumbnail; filters by status when `?status=…` present
- [X] T068 [P] [US4] Frontend unit test `<ProjectDetailPage>` in `app/tests/frontend/Unit/ProjectDetailPage.test.tsx`: shows thumbnail + status + "Publish" button when `ready-to-publish`; shows error reason when `failed`; does NOT embed `<ModelViewer>` (admin page is for management only — viewing is on the public SharePage)
- [X] T069 [P] [US4] Frontend unit test `<ShareDialog>` in `app/tests/frontend/Unit/ShareDialog.test.tsx`: renders the QR PNG image, the public URL with a "Copy" button that writes to the clipboard mock

### Implementation for User Story 4

- [X] T070 [P] [US4] Create `<DropZone>` component in `app/frontend/src/components/DropZone.tsx`: drag-and-drop + click-to-pick, accepts only `.ifc`, validates size client-side, emits `onSelect(File)` with progress events
- [X] T071 [P] [US4] Create `<ShareDialog>` component in `app/frontend/src/components/ShareDialog.tsx`: modal showing QR PNG, public URL with copy-to-clipboard, "Close" button; opens via `open={true}` prop
- [X] T072 [P] [US4] Create `<DashboardPage>` in `app/frontend/src/pages/DashboardPage.tsx`: list view with `<StatusBadge>`, thumbnail, name, date; "New project" button → `/upload`; "View" → `/projects/{id}`; "Share" → opens `<ShareDialog>` after `publishProject(id)`
- [X] T073 [P] [US4] Create `<ProjectDetailPage>` in `app/frontend/src/pages/ProjectDetailPage.tsx`: shows thumbnail, status, error reason if failed, "Publish" button (calls `publishProject(id)` then opens `<ShareDialog>`), "Show share link" button for published projects; does NOT embed `<ModelViewer>` (admin page is for management only — viewing is on the public SharePage)
- [X] T074 [P] [US4] Create `<UploadPage>` in `app/frontend/src/pages/UploadPage.tsx`: form with `name`, `description`, `clientLabel` fields + `<DropZone>`; submits via `createProject(...)` (multipart); shows progress; on 201 navigates to `/projects/{id}`
- [X] T075 [P] [US4] Create `<LoginPage>` in `app/frontend/src/pages/LoginPage.tsx` + `<RegisterPage>` in `app/frontend/src/pages/RegisterPage.tsx`: form posts to `/auth/login` / `/auth/register`; on success, navigates to `/`
- [X] T076 [US4] Update `app/frontend/src/api/client.ts`: add `createProject(formData)`, `getProject(id)`, `listProjects(opts)`, `publishProject(id)` wrappers; ensure `X-Correlation-Id` is sent on every request
- [X] T077 [US4] Update `app/frontend/src/App.tsx` routes: `/` → `DashboardPage`, `/upload` → `UploadPage`, `/projects/:id` → `ProjectDetailPage`, `/login` → `LoginPage`, `/register` → `RegisterPage`; add a protected-route wrapper that redirects to `/login` if `/api/projects` returns 401
- [X] T078 [US4] Add `app/frontend/src/auth/useCurrentUser.ts`: a small hook that returns the current user (or `null`); backed by a one-time `GET /api/me` endpoint or a `/auth/me` Identity-style endpoint

**Checkpoint**: The architect can manage projects end-to-end from the dashboard.

---

## Phase 7: User Story 5 — Multi-tenancy / data isolation (Priority: P3)

**Goal**: Projects, files, and public links are scoped to a tenant (the architect's account). One tenant cannot see or modify another tenant's data. Public links expose only what is strictly necessary — no internal IDs, no tenant metadata.

**Independent Test**: Create two users. As user A, create+publish a project. As user B, attempt `GET /api/projects/{A's project id}` → 404. As user B, attempt to guess A's `publicToken` 1,000,000 times → 0 hits. The public page response from A's token contains no `id`, `ownerId`, or `errorMessage`.

### Tests for User Story 5 ⚠️

- [X] T079 [P] [US5] Integration test cross-tenant isolation in `app/tests/backend/Integration/TenantIsolationTests.cs`: register two users, create+publish a project as user A, attempt `GET /api/projects/{A's id}` as user B → 404; attempt `POST /api/projects/{A's id}/publish` as user B → 404; attempt `GET /api/share/{A's publicToken}` as user B → 200 (public, anonymous) but `GET /api/projects/{A's id}` as user B → 404 (private)
- [X] T080 [P] [US5] Integration test unguessable tokens in `app/tests/backend/Integration/TokenUnguessabilityTests.cs`: hit `GET /api/share/{random-guid}` 10,000 times, assert all 10,000 return 404 (SC-005; the unique index on `PublicToken` ensures O(1) lookup)
- [X] T081 [P] [US5] Integration test public-page no-leak in `app/tests/backend/Integration/PublicShareNoLeakTests.cs`: parse the response of `GET /api/share/{token}` and assert the JSON has ONLY `name`, `clientLabel`, `status`, `glbUrl`, `thumbnailUrl` keys — fail on any other key (FR-025)
- [X] T082 [P] [US5] Contract test for tenant scoping in `app/tests/backend/Contract/TenantScopingContractTests.cs`: assert `GET /api/projects` returns only the calling user's projects (zero cross-tenant items in `items`)

### Implementation for User Story 5

- [X] T083 [US5] Add a global query filter in `app/backend/Infrastructure/AppDbContext.cs` on `Project` and `ShareLink`: `e => e.OwnerId == _currentUserId` (or `Project.OwnerId` for `ShareLink`); inject `ICurrentUser` to read the current user id
- [X] T084 [US5] Add `ICurrentUser` interface in `app/backend/Application/Abstractions/ICurrentUser.cs` with `Guid Id { get; }`; implement in `app/backend/Infrastructure/CurrentUser.cs` reading `HttpContext.User`
- [X] T085 [P] [US5] Add a `GET /api/me` endpoint in `app/backend/Api/Endpoints/AuthEndpoints.cs` returning `{ "id": "...", "email": "..." }`; gated by `[Authorize]`
- [X] T086 [P] [US5] Update `PublishProjectHandler` and `GetProjectHandler` to confirm cross-tenant lookups return 404 (not 403); tests in T079 enforce this
- [X] T087 [P] [US5] Update `PublicShareHandler` to drop the `Metadata` block from any future expanded response — already absent in `contracts/openapi.md §GET /api/share/{token}`

**Checkpoint**: Tenants are isolated; public pages leak nothing.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Spec compliance, repo hygiene, observability, and the e2e validation per `quickstart.md`. Affects multiple stories.

- [X] T088 [P] Rewrite `app/README.md` removing all "BIM platform", "BIM collaboration", "BIM coordination", "BIM metadata", "BIM management", "BIM engineering" wording per FR-031 and SC-008; describe the product as "3D model sharing for architecture, interiors, and custom furniture"
- [X] T089 [P] Remove dead BIM components: delete `app/frontend/src/components/PropertiesPanel.tsx` and `app/frontend/src/components/SpatialTree.tsx` (FR-020 forbids them; their only consumer is the to-be-rewritten `ViewerPage`); remove the click-to-pick raycaster code in `app/frontend/src/pages/ViewerPage.tsx` (lines 33-36, 147-200) and the `selectedElement` state
- [X] T090 [P] Remove stale CSS classes from `app/frontend/src/App.css`: `.tree-item`, `.tree-children`, `.property-row`, `.property-label`, `.property-value`, `.viewer-panel`, `.panel-header`, `.panel-content`, `.panel-toggle`, `.badge-uploaded`, `.badge-queued`, `.badge-completed` (replaced by the new status names)
- [X] T091 [P] Drop unused dependencies from `app/frontend/package.json`: `three`, `@types/three` (no longer imported after T089)
- [X] T092 [P] Remove `app/.env` and `app/backend/.env` from git tracking (`git rm --cached`); add `.env` to top-level `.gitignore` (the file contains default creds — `arch3dar_secret` / `minioadmin`; security risk)
- [X] T093 [P] Switch `app/converter/converter_service.py` to JSON structured logging with `correlation_id` field; emit the same correlation id read from the row's `correlation_id` column (set by the backend at upload time)
- [X] T094 [P] Switch `app/backend/Api/Program.cs` `Database.Migrate()` call site to a startup hosted service so migrations run before `app.Run()` returns (graceful startup ordering; replaces any `EnsureCreated()` remnants)
- [X] T095 [P] Add `GET /api/me` rate limiting (1 req/s per IP) and a basic CORS allow-list from `CORS_ALLOWED_ORIGINS` env (defaults to `http://localhost:3000`); reject all other origins in dev
- [X] T096 [P] Add Serilog enrichment: `ProjectId`, `OwnerId`, `PublicToken` (only for share endpoints) pushed into `LogContext` per request via a custom middleware that runs after `CorrelationIdMiddleware`
- [X] T097 [P] Wire `dotnet ef migrations bundle` or a `migrate-on-startup` so a fresh `docker compose up` brings a fresh DB up to head (no manual `dotnet ef database update` step in `quickstart.md` step 0)
- [X] T098 [P] Add a Makefile `app/Makefile` with targets `make up`, `make down`, `make logs`, `make test-backend`, `make test-frontend`, `make e2e`, `make audit-bim` (the last one greps for forbidden terms and exits 1 on hits; supports SC-008 verification)
- [X] T099 [P] Add `app/frontend/src/pages/NotFoundPage.tsx`: a friendly "we couldn't find that project" page used by the `*` route (US-2 AC-5)
- [X] T100 Run the full `quickstart.md` validation end-to-end on a clean clone; verify all 17 acceptance-criteria checkboxes from `quickstart.md §What "done" looks like` pass; verify `make audit-bim` returns zero hits
- [X] T101 Final review: confirm every file path in this `tasks.md` exists in the final tree; remove any task whose target file was deleted; commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. T001 → T011 are all independent.
- **Foundational (Phase 2)**: Depends on Setup completion. T012–T030 BLOCKS all user stories. T012, T013, T014, T015, T016, T017, T018, T019, T020 can run in parallel; T021–T024 depend on the Domain/Application/Infrastructure work; T025–T030 can run in parallel with the backend work.
- **User Stories (Phase 3–7)**: All depend on Foundational phase completion. They can proceed in parallel (if staffed) or sequentially in priority order (P1×3 → P2 → P3).
- **Polish (Phase 8)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only. No dependencies on other stories.
- **US2 (P1)**: Depends on Phase 2 only. Reads the GLB/thumbnail that US1 produces, but is independently testable: a manually inserted `ShareLink` + a presigned GLB key in MinIO is enough.
- **US3 (P1)**: Depends on Phase 2 only AND on the `<ModelViewer>` from US2. The AR capability hook (T062) is independent; the wiring into `<ModelViewer>` (T063) requires T053.
- **US4 (P2)**: Depends on Phase 2 AND on US1 (uses `createProject`, `publishProject`). Independently testable by mocking the API client.
- **US5 (P3)**: Depends on Phase 2 AND on US1 (publish endpoint creates the `ShareLink` it tests). Independently testable once the auth + global query filter exist.

### Within Each User Story

1. Tests (T031–T036 for US1, T046–T050 for US2, T060–T061 for US3, T066–T069 for US4, T079–T082 for US5) MUST be written first and confirmed to FAIL before implementation.
2. Domain/Application code (handlers, validators, DTOs) before API endpoints.
3. API endpoints before frontend consumers.
4. Each story's checkpoint is verified before moving on.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005, T006, T007, T008, T009, T010, T011 are all `[P]` and can run in parallel.
- **Phase 2**: T013, T014, T015, T016, T017, T018, T019, T020 are `[P]`. T025, T026, T027, T028, T029, T030 are `[P]` (separate test/converter/docker scope).
- **Across user stories**: Once Phase 2 completes, the five user stories can run in parallel with five developers. Within each story, all `[P]` test/model/service tasks can run in parallel.
- **Polish phase**: T088, T089, T090, T091, T092, T093, T095, T096, T097, T098, T099 are `[P]`.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together (T031–T036 are [P]):
Task: "T031 [P] [US1] Unit test Project.TransitionTo in app/tests/backend/Unit/ProjectStateTransitionTests.cs"
Task: "T032 [P] [US1] Unit test publish idempotency in app/tests/backend/Unit/PublishProjectHandlerTests.cs"
Task: "T033 [P] [US1] Integration test upload+convert+publish in app/tests/backend/Integration/ProjectLifecycleTests.cs"
Task: "T034 [P] [US1] Integration test upload validation in app/tests/backend/Integration/UploadValidationTests.cs"
Task: "T035 [P] [US1] Integration test conversion failure in app/tests/backend/Integration/ConversionFailureTests.cs"
Task: "T036 [P] [US1] Contract test POST /api/projects in app/tests/backend/Contract/CreateProjectContractTests.cs"

# Launch all handlers/validators for US1 together (T037–T042 are [P]):
Task: "T037 [P] [US1] CreateProjectHandler in app/backend/Application/Projects/Commands/CreateProjectHandler.cs"
Task: "T038 [P] [US1] CreateProjectValidator in app/backend/Application/Projects/Validators/CreateProjectValidator.cs"
Task: "T039 [P] [US1] PublishProjectHandler in app/backend/Application/Projects/Commands/PublishProjectHandler.cs"
Task: "T040 [P] [US1] PublishProjectValidator in app/backend/Application/Projects/Validators/PublishProjectValidator.cs"
Task: "T041 [P] [US1] GetProjectHandler in app/backend/Application/Projects/Queries/GetProjectHandler.cs"
Task: "T042 [P] [US1] ListProjectsHandler in app/backend/Application/Projects/Queries/ListProjectsHandler.cs"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3 — all P1)

The MVP is **all three P1 stories together**: an architect publishes a project (US1), the client opens the public link and views the 3D model (US2), and the client opens it in AR (US3). Without all three, the product is incomplete. A single-client demo end-to-end is the bar.

1. Complete Phase 1: Setup (T001–T011)
2. Complete Phase 2: Foundational (T012–T030)
3. Complete Phase 3: US1 — upload + convert + publish (T031–T045)
4. Complete Phase 4: US2 — public 3D viewing (T046–T059)
5. Complete Phase 5: US3 — AR handoff (T060–T065)
6. **STOP and VALIDATE**: run `quickstart.md` steps 1–9 on a clean clone. All P1 acceptance criteria pass. **MVP ready.**

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001–T030)
2. Add US1 → independently testable; client can see a public link but no 3D model yet
3. Add US2 → client can view the 3D model on the public page
4. Add US3 → client can launch AR (MVP complete)
5. Add US4 (P2) → architect has a real dashboard UX
6. Add US5 (P3) → multi-tenant isolation hardened
7. Polish (Phase 8) → repo hygiene + spec compliance + final validation

### Parallel Team Strategy

With three developers:

1. Team completes Setup + Foundational together (T001–T030)
2. Once Foundational is done:
   - **Developer A**: US1 (P1) — backend, conversion, publish (T031–T045)
   - **Developer B**: US2 (P1) — public page, viewer wrapper (T046–T059) — can mock the API until A finishes
   - **Developer C**: US4 (P2) — dashboard, upload form (T066–T078) — can mock the API
3. After US1 ships, US3 (T060–T065) is a 1-day wiring job (AR handoff) and US5 (T079–T087) is a 1-day hardening pass
4. Polish (Phase 8) is a 1–2 day final pass by anyone

---

## Notes

- `[P]` tasks touch different files and have no intra-phase dependencies. Tasks without `[P]` either depend on earlier tasks in the same phase or are the integration point that wires parallel work together.
- `[US1]…[US5]` labels map directly to the user stories in `spec.md` §User Scenarios & Testing.
- Every task has an exact file path. An LLM should be able to start each task without further context.
- Each user story has its own checkpoint — stop, run the tests, and verify the story works on its own before moving to the next priority.
- Commit after each task or logical group (the optional `/speckit.git.commit` post-task hook can be invoked per task).
- T100 is the final integration gate: it is a manual run of `quickstart.md` plus a `make audit-bim` (added in T098) to confirm SC-008.
- T101 is the final hygiene pass — verify the produced tree matches every path mentioned in this file and remove stale tasks.
