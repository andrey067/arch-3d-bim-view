# Implementation Plan: Arch3DAR — IFC-to-AR 3D Sharing MVP

**Branch**: `001-ifc-mvp-platform` | **Date**: 2026-06-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-ifc-mvp-platform/spec.md`

## Summary

Arch3DAR is a SaaS MVP that lets architects, interior designers, and custom-furniture manufacturers share a single 3D model (IFC input) with a client through an unguessable public link + AR view. The MVP is one backend (ASP.NET Core 9 + MediatR + EF Core + Serilog + QRCoder), one React/Vite frontend (using `<model-viewer>` for 3D + AR), one Python sidecar (IfcOpenShell `IfcConvert`), MinIO for object storage, and PostgreSQL for relational state. A `FOR UPDATE SKIP LOCKED` claim in Postgres is the only queue — no Redis, no RabbitMQ. The converter is hidden behind a single `IModelConverter` interface so future formats (SKP, RVT, DWG, DXF, OBJ, STL, DAE, FBX) can be added without touching upload/share code. The product is explicitly *not* a BIM platform: the viewer has no properties tree, no element metadata, no measurement, and no clash tools; all user-facing copy avoids the word "BIM".

## Technical Context

**Language/Version**: C# 13 / .NET 9 (`net9.0`) for the backend; TypeScript 5 / React 18 + Vite for the frontend; Python 3.11 for the converter sidecar.

**Primary Dependencies**:
- Backend: `Microsoft.AspNetCore.Identity.EntityFrameworkCore` 9.x, `Microsoft.EntityFrameworkCore.Design` 9.x, `Npgsql.EntityFrameworkCore.PostgreSQL` 9.x, `MediatR` 14.x, `QRCoder` 1.8.x, `Serilog.AspNetCore` 9.x, `Minio` 6.0.x, `FluentValidation.AspNetCore` 11.x.
- Frontend: `react@18`, `react-router-dom@6`, `@google/model-viewer@3.3`, `axios@1.6`, `vitest`, `@testing-library/react`, `@playwright/test`.
- Converter: `ifcopenshell` (Python wheel) and the `IfcConvert` Linux64 binary.

**Storage**:
- PostgreSQL 16 (relational state: `projects`, `share_links`, ASP.NET Identity tables).
- MinIO (object storage: 4 buckets — `ifc-files`, `glb-files`, `thumbnails`, `qrcodes`).
- All public deliverable assets served via 5–15 min presigned MinIO URLs. The backend never proxies binary content.

**Testing**:
- Backend: xUnit + FluentAssertions + Testcontainers (Postgres, MinIO) for integration tests; real Python converter sidecar in one Testcontainer for the round-trip test.
- Frontend: Vitest + React Testing Library for components, Playwright for the public-page e2e.

**Target Platform**: Linux server (Docker Compose on a single VM for MVP). Browsers: Chrome 100+ / Safari 15+ / Firefox 100+ (mobile-first for AR).

**Project Type**: Web application (frontend SPA + backend API + worker service).

**Performance Goals**:
- SC-001: end-to-end "open dashboard → client sees public link" in < 5 min for a 50 MB IFC on 10 Mbps up.
- SC-003: public page (thumbnail + 3D model) loads in < 10 s on 4G.
- Backend request p95 < 200 ms for read paths; upload latency dominated by the client's uplink.

**Constraints**:
- FR-004: max upload 100 MB (env-configurable, default).
- 5-min conversion timeout; 2 retry attempts before `failed`.
- No cookies/storage on the public page; no client-side state, no third-party analytics.
- Tenant isolation mandatory (SC-006): cross-tenant reads return 404 (not 403, to avoid enumeration).

**Scale/Scope**:
- MVP target: 1 architect, 10 concurrent clients, 100 projects. Throughput: ≤ 1 conversion/min.
- 33 functional requirements (FR-001…FR-033); 5 P1 user stories + 1 P2 + 1 P3.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Clean Code & MVP Pragmatism** | ✅ Pass | Single Backend project, folder-based layers (no premature 4-project split). YAGNI applied to CQRS (no `IRepository<T>`), ValueObject base class, or AggregateRoot base class. Postgres `FOR UPDATE SKIP LOCKED` chosen over Redis/RabbitMQ because the throughput does not justify the extra service. The converter sidecar is kept separate (not merged into the API image) to avoid dragging IfcConvert + OpenCascade into the API image. |
| **II. Meaningful Naming & Structure** | ✅ Pass | Folder layout: `Domain/`, `Application/`, `Infrastructure/`, `Api/`. Files named by their role: `CreateProjectHandler`, `TransitionTo`, `HttpModelConverter`, `MinioService`. Status enum is `ProjectStatus` (not `ProjectStateEnum`); public share row is `ShareLink` (not `PublicShareLinkEntity`). No abbreviations except `Id`, `Url`, `Http`. |
| **III. Small Units & Single Responsibility** | ✅ Pass | Backend `Program.cs` is split into `Api/Endpoints/...` partial files. The state machine is a single `Project.TransitionTo(...)` method. The converter has one job: claim → run → upload → update. The viewer page is one component. No component exceeds 150 lines. |
| **IV. Tests Mirror Structure** | ✅ Pass | `app/tests/backend/{Unit,Integration,Contract}/` and `app/tests/frontend/{Unit,E2E}/`. xUnit + FluentAssertions on the backend, Vitest + RTL on the frontend, Playwright for e2e. |
| **V. Self-Documenting Code & Minimal Comments** | ✅ Pass | Comments will explain WHY (e.g., "Presigned URL with 5 min TTL — backend must not proxy the binary to keep p95 < 200 ms"). No code parroted. No commented-out code in shipped branches. |

**Constitution re-check after Phase 1 design**: All 5 principles still pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-ifc-mvp-platform/
├── plan.md              # This file
├── research.md          # Phase 0 — all 10 technical decisions justified
├── data-model.md        # Phase 1 — entities, validation, state machine
├── contracts/
│   └── openapi.md       # Phase 1 — HTTP API + Python converter contract
├── quickstart.md        # Phase 1 — runnable end-to-end validation
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── spec.md              # Already written
```

### Source Code (repository root)

The existing repo already uses the constitution's mandated `app/{backend,frontend,converter,tests}/nginx/` layout. We **keep it** — no reshuffling — and migrate the contents incrementally (see `research.md` §R-10 and the GAP report's 8-step migration proposal).

```text
app/
├── backend/                        # ASP.NET Core 9 API
│   ├── Domain/
│   │   ├── Project.cs              # entity + TransitionTo state machine
│   │   └── ProjectStatus.cs        # enum
│   ├── Application/
│   │   ├── Abstractions/
│   │   │   └── IModelConverter.cs  # seam for future formats (FR-029)
│   │   ├── Projects/
│   │   │   ├── Commands/
│   │   │   │   ├── CreateProjectHandler.cs
│   │   │   │   └── PublishProjectHandler.cs
│   │   │   ├── Queries/
│   │   │   │   ├── GetProjectHandler.cs
│   │   │   │   └── ListProjectsHandler.cs
│   │   │   ├── Validators/
│   │   │   └── Dtos/
│   │   └── Sharing/
│   │       ├── PublicShareHandler.cs
│   │       └── Dtos/
│   ├── Infrastructure/
│   │   ├── AppDbContext.cs
│   │   ├── Migrations/
│   │   ├── HttpModelConverter.cs   # IModelConverter impl (Python sidecar)
│   │   ├── MinioService.cs
│   │   ├── QrCodeService.cs        # QRCoder wrapper
│   │   └── CorrelationIdMiddleware.cs
│   ├── Api/
│   │   ├── Program.cs
│   │   └── Endpoints/
│   │       ├── AuthEndpoints.cs
│   │       ├── ProjectsEndpoints.cs
│   │       └── PublicShareEndpoints.cs
│   ├── Backend.csproj
│   └── Dockerfile
│
├── converter/                      # Python 3.11 + IfcOpenShell
│   ├── converter_service.py        # new: IConverter + claim loop + HTTP API
│   ├── converter.py                # 10-line shim re-exporting converter_service
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # React 18 + Vite + <model-viewer>
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx       # list + status
│   │   │   ├── ProjectDetailPage.tsx   # status + publish action
│   │   │   ├── UploadPage.tsx          # drag-drop + form
│   │   │   ├── SharePage.tsx           # public page with <model-viewer>
│   │   │   ├── LoginPage.tsx
│   │   │   └── NotFoundPage.tsx
│   │   ├── components/
│   │   │   ├── ModelViewer.tsx         # <model-viewer> wrapper
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── ShareDialog.tsx         # QR + copy-to-clipboard
│   │   │   └── DropZone.tsx
│   │   ├── api/
│   │   │   └── client.ts                # axios + types + X-Correlation-Id
│   │   ├── auth/
│   │   │   └── useCurrentUser.ts
│   │   └── App.tsx
│   └── package.json
│
├── tests/
│   ├── backend/
│   │   ├── Unit/                   # state machine, validators
│   │   ├── Integration/            # WebApplicationFactory + Testcontainers
│   │   │   └── Fixtures/sample.ifc
│   │   └── Contract/               # JSON snapshot tests for API responses
│   └── frontend/
│       ├── Unit/                   # Vitest + RTL
│       └── E2E/                    # Playwright public-page happy path
│
├── nginx/                          # production-only compose (out of scope for dev)
├── docker-compose.yml              # 5 services
├── .env.example
└── README.md
```

**Structure Decision**: Adopt **Option 2 (Web application)**. The current layout already matches the constitution's mandated `app/{backend,frontend,converter,tests}/` split. We retain it verbatim and migrate file contents in place — no directory moves, no rename of `app/`. The only structural change is the **internal** layering inside `app/backend/` (Domain/Application/Infrastructure/Api folders) — no new top-level directories are introduced.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No Constitution violations. The plan respects:
- **Single project** for the backend (vs. 4-project split).
- **Postgres queue** (vs. RabbitMQ/Redis).
- **Folder-based layers** inside one project (vs. multiple assemblies enforcing the boundary at compile time).
- **`<model-viewer>`** as a web component (vs. a custom Three.js viewer).

Each of these is the simplest thing that satisfies the 33 functional requirements without violating the spec's measurable outcomes (SC-001…SC-008). The GAP report (8 migration steps) is the ordered plan for getting the existing partial code from "BIM viewer with sequential public URLs and a Python script" to "no-BIM viewer with unguessable URLs and a stable worker". Every step is independently shippable.
