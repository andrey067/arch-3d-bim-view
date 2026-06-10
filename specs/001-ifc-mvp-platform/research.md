# Research: Arch3DAR MVP

**Phase**: 0
**Branch**: `001-ifc-mvp-platform`
**Date**: 2026-06-09
**Spec**: `specs/001-ifc-mvp-platform/spec.md`

> Resolves every `NEEDS CLARIFICATION` in the Technical Context. All decisions are MVP-graded: chosen for time-to-market, reversible, and aligned with `.specify/memory/constitution.md` §I (YAGNI / MVP-pragmatism).

---

## R-01. Backend framework + in-process messaging + layering

**Decision**
- **ASP.NET Core 9** (`net9.0`).
- **MediatR 14.x** registered once (`cfg.RegisterServicesFromAssembly(typeof(Program).Assembly)`); handlers auto-discovered. `IMediator` is `Transient`.
- **Single Backend project** at `app/backend/Backend.csproj` with folder-based layers:
  ```
  app/backend/
  ├── Domain/         # entities + state machine, no EF annotations
  ├── Application/    # commands, queries, handlers, validators, abstractions
  ├── Infrastructure/ # EF Core DbContext, MinIO, QRCoder, converter HTTP client
  └── Api/            # minimal-API endpoints, ProblemDetails, auth, Serilog
  ```
- **Thin Domain**: a `Project` entity with a `TransitionTo(ProjectStatus next)` method that validates the state machine. No `AggregateRoot<T>` base class, no `ValueObject` base class, no `IRepository<T>` over EF — `AppDbContext` is used directly inside handlers. The conversion-completed event is dispatched via `INotification`.

**Rationale**
- The spec is CRUD + a 5-state machine. Full DDD ceremony adds days and observable behaviour = none at this scale.
- A single project respects the constitution's MVP-pragmatism rule: smaller Docker build, one `dotnet test` invocation, one migration project.
- MediatR 14.x is still the de-facto in-process dispatcher (2.6K dependents). The license is source-available but suppressible per the package docs; the spec says "ASP.NET Core + MediatR" so we honour that.

**Alternatives considered**
- **Wolverine** (MIT, mediator+handler+outbox+saga in one): drops the MediatR license question. Rejected: learning surface + features we don't use.
- **4-project split (Domain/Application/Infrastructure/Api)**: zero value for a 33-FR CRUD app, triples the build graph, forces `-p` on `dotnet ef migrations add`.
- **Source-generated dispatcher (Mediator by Martin Othamar)**: AOT-friendly but not a real migration path for the partial code we have, and AOT is not a 2026 MVP goal.

---

## R-02. Storage layout

**Decision**
- **Four MinIO buckets**, one per concern:
  - `ifc-files` — original uploaded IFC (long retention)
  - `glb-files` — generated 3D model
  - `thumbnails` — preview PNG
  - `qrcodes` — generated QR PNG
- **Key layout**: `{bucket}/projects/{projectId}/{role}.{ext}` — e.g. `ifc-files/projects/{guid}/source.ifc`, `glb-files/projects/{guid}/model.glb`, `thumbnails/projects/{guid}/thumb.png`, `qrcodes/projects/{guid}/qr.png`.
- **Public delivery via presigned MinIO URLs** with a 5–15 min TTL, re-presigned on every public-page request. The browser fetches the GLB directly from MinIO; the backend never proxies the binary.
- The MinIO endpoint must be reachable from the public internet. For dev this means port-forward / Cloudflare Tunnel; for prod it's the same hostname behind TLS.

**Rationale**
- One-bucket-with-prefixes scales, but per-bucket doubles as a policy boundary (different lifecycle/expiration rules per concern). Splitting buckets is one line in docker-compose and zero in code; collapsing them later is a one-time data migration.
- Presigned-URL delivery keeps the ASP.NET host from becoming a bandwidth bottleneck for 50–500 MB GLBs and is the only way SC-003 (<10 s on 4G) is realistically achievable. `model-viewer`'s range-request streaming is preserved.
- Tenant isolation is enforced by the presign being generated only for projects the requesting tenant owns (auth) or is `Published` (public).

**Alternatives considered**
- Single bucket with prefixes: rejected — lifecycle story gets awkward, policy rules get noisier.
- Backend proxy of the GLB: rejected — doubles bandwidth, breaks `model-viewer` range requests, adds streaming bugs.
- CloudFront/NGINX in front of MinIO: out of scope for MVP.

---

## R-03. Conversion worker integration

**Decision**
- **Keep the Python converter as a separate container.** Do not merge it into the .NET backend image (the IfcConvert binary + OpenCascade + Python 3 = ~600 MB, with a different operational class of failure modes).
- **Replace the polling trigger with a Postgres `FOR UPDATE SKIP LOCKED` claim.** The converter polls every 2 s for `Status = 'UploadReceived'` rows, claims one with `SKIP LOCKED`, sets `Status = 'Processing'`, runs the conversion, then sets `Status = 'ReadyToPublish'` (success) or `Status = 'Failed'` (with `ErrorMessage`).
- **The .NET side owns the `IModelConverter` abstraction**:
  ```csharp
  public interface IModelConverter
  {
      Task<ConversionResult> ConvertAsync(
          Guid projectId, CancellationToken ct);
  }
  public sealed record ConversionResult(
      string GlbObjectKey, string ThumbnailObjectKey, long DurationMs);
  ```
  The MVP has one implementation: `HttpModelConverter` which POSTs the projectId to the converter's HTTP API (`http://converter:8080/convert`) and receives `{ glbKey, thumbKey, durationMs }` back. Adding a new format later is a new `IModelConverter` implementation and a registration — no change to upload/share code.
- **Single source of truth for state** is the `Projects` table. No `Jobs` table, no Redis, no RabbitMQ.

**Rationale**
- Postgres `FOR UPDATE SKIP LOCKED` is the cheapest durable queue that satisfies "no message loss + no double-processing" and we already run Postgres.
- `Channel<T>` is rejected because the conversion runs in a different container; in-process queues can't cross that boundary.
- The "store IFC, separate worker picks it up" pattern already exists in the current code; the only change is making the trigger explicit (a status row) instead of a 10-second poll on `Status IN ('Uploaded', 'Queued')`.
- IModelConverter is the seam FR-010/FR-029/FR-030 mandate. It also makes the .NET unit tests trivial (fake `IModelConverter` returns canned bytes) without the integration tests having to embed a real Python process.
- Status surfacing: dashboard polls `GET /api/projects/{id}` every 2 s while in `UploadReceived`/`Processing`; no WebSocket needed for MVP. SC-002's "no project stuck in processing" guarantee is enforced by a 5-minute watchdog inside the converter itself: a `Processing` row older than 5 minutes is re-claimed and retried up to 2 times before being marked `Failed` with reason `"conversion-timeout"`.

**Alternatives considered**
- **Backend calls `IfcConvert` via `Process.Start`**: rejected — drags ~600 MB of native binaries into the API image, cross-platform `Process.Start` is fragile, and it couples the conversion upgrade path to the API release cycle (wrong direction for FR-010).
- **RabbitMQ or Redis Streams**: rejected — another container, another secret, the throughput (≤ 1 conversion/min in MVP) does not justify it.
- **Inline conversion in .NET via `python.NET` + IfcOpenShell**: rejected — adds a 600 MB native dep to the API image, lengthens cold start, and is a different runtime from what we already operate.
- **Hangfire + Postgres storage**: rejected — brings a dashboard, retries, continuations we don't need.

---

## R-04. IFC → GLB conversion tool

**Decision**
- **Primary: IfcOpenShell's `IfcConvert` CLI** (current `v0.8.0`). The converter calls `IfcConvert model.ifc model.glb` for the GLB and `IfcConvert model.ifc thumb.png --thumbnail` for the thumbnail.
- **Fallback: IfcOpenShell Python API** (already in the `ifcopenshell` pip wheel). Used if the CLI's `--thumbnail` flag is unavailable in the deployed build.
- **Run as a CLI invoked from a Python sidecar** — the same pattern the current code already uses. Each conversion spawns `IfcConvert` as a subprocess with a timeout, captures stderr, exits.
- The Python sidecar exposes a minimal HTTP surface (`POST /convert` with `project_id`, returns `{ glbKey, thumbKey, durationMs }`) so the .NET `IModelConverter` implementation can be a thin HTTP client. The HTTP surface is a FastAPI one-file app.

**Rationale**
- IfcOpenShell v0.8.0 parses IFC2x3 TC1, IFC4 Add2 TC1, IFC4x1, IFC4x2, IFC4x3 Add2. Geometry support is extensive for IFC2x3 and IFC4 — the two schemas produced by SketchUp/Revit/AutoCAD/ArchiCAD/Blender, which is the spec's input universe.
- `IfcConvert` outputs glTF/GLB natively with the `.glb` extension, including material binding from `IfcSurfaceStyleRendering`. This is exactly what `model-viewer` and AR Quick Look consume.
- CLI invocation is operationally simpler than a long-lived Python HTTP service for a single binary, single output format. The HTTP wrapper exists only because the .NET side mandates `IModelConverter` (FR-029).

**Alternatives considered**
- **Bonsai (Blender IFC add-on)**: production-quality IFC authoring in Blender, but a full Blender install is unjustifiable for a render-only path.
- **Xbim (native .NET IFC parser)**: outputs BREP/NURBS, not GLB; would need a separate tessellator + glTF writer.
- **Headless Three.js in Node**: same problem as Blender, with a worse IFC story.

---

## R-05. QR code generation

**Decision**
- **QRCoder 1.8.0** (MIT, zero dependencies, PNG output). Use `PngByteQRCodeHelper.GetQRCode(url, ECCLevel.Q, pixelsPerModule: 20)` or the equivalent `new PngByteQRCode(...).GetGraphic(20)` for explicit control.
- Upload the resulting `byte[]` to the `qrcodes` bucket with `ContentType=image/png` and serve via presigned URL like any other artifact.

**Rationale**
- QRCoder's `PngByteQRCode` renderer does not require `System.Drawing.Common` (which is Windows-only since .NET 6). This matters because the backend runs on Linux.
- ECC level `Q` (25 % redundancy) is the right default for printable QR codes — survives partial occlusion on a printed page and most camera lenses. `pixelsPerModule: 20` produces a ~400 px PNG at the default URL length, which is plenty for screen display and small print.
- ZXing.Net is a reader-focused library; its generation path is awkward and historically less maintained.

**Alternatives considered**
- **ZXing.Net**: not its strength, more boilerplate, less maintained.
- **SkiaSharp + manual encoding**: reinvents the wheel, would need its own Reed-Solomon implementation.
- **Server-side SVG**: only useful if we later need to embed the QR on a printable PDF (out of scope for MVP).

---

## R-06. Frontend 3D viewer

**Decision**
- **`<model-viewer>`** (Google, Apache-2.0, ~3.3.0). One custom element, imported as an ESM module. Render as:
  ```html
  <model-viewer
    src={glbUrl}
    poster={thumbnailUrl}
    ar
    ar-modes="webxr scene-viewer quick-look"
    camera-controls
    autoplay
    shadow-intensity="1">
  </model-viewer>
  ```
- Drop the existing Three.js viewer (currently `ViewerPage.tsx`) and the `PropertiesPanel` + `SpatialTree` components — FR-020 forbids them.
- Drop `three` and `@types/three` from `package.json` once the BIM viewer is removed.
- For iOS, ship the GLB-only path in MVP and surface a banner ("Open in AR works best on Android Chrome"). Adding a USDZ companion file is a post-MVP quality task.

**Rationale**
- AR handoff on both platforms is one attribute (`ar` + `ar-modes`). SC-004 ("AR handoff that places the model at real-world scale") is satisfied by `scene-viewer` (Android ARCore) and `quick-look` (iOS).
- Orbit/zoom/pan/fullscreen are built into `camera-controls` + the default UI; FR-016, FR-017 are zero code.
- The "no BIM features" constraint (FR-020) is satisfied by default — model-viewer has no properties tree, no measurement, no clash tools.

**Alternatives considered**
- **Three.js + custom AR handoff**: rejected — requires a Scene Viewer intent URL builder, a separate Quick Look `<a rel="ar" href="…usdz…">` element, and a custom orbit-control implementation. Recreates model-viewer badly, costs 2–3 days, and adds a Three.js dependency the MVP cannot justify.

---

## R-07. Public share token

**Decision**
- **GUID v4** (`Guid.NewGuid()`) stored as a 36-char `D`-formatted string on a separate `ShareLinks` table:
  ```csharp
  public sealed class ShareLink
  {
      public Guid Id { get; set; }
      public Guid ProjectId { get; set; }
      public Guid PublicToken { get; set; }   // unguessable, 122 bits entropy
      public DateTimeOffset CreatedAt { get; set; }
  }
  ```
- Public URL: `https://{PUBLIC_BASE_URL}/s/{PublicToken}`.
- On `POST /api/projects/{id}/publish`, look up `ShareLinks` by `ProjectId`; if present return the existing token/QR; else create a new one. Idempotent (FR-013).

**Rationale**
- FR-014 requires "non-sequential, unguessable, no internal DB IDs". Guid v4 has 122 bits of entropy — SC-005's "1,000,000 random URLs has effectively 0% chance" is satisfied with 122 bits (~4×10⁻³¹). Implementation is one line; no NuGet.
- The token is the **PublicToken** (a second Guid), not the ProjectId, satisfying "MUST NOT expose internal database IDs" (FR-014, FR-025).

**Alternatives considered**
- **ULID** (Crockford base-32, 26 chars, sortable, ~128 bits): requires the `Ulid` NuGet, offers only sortability (unused). Adds a dep for zero observable benefit.
- **NanoID (21 chars)**: same unguessability as Guid v4 at slightly shorter URL length. YAGNI.
- **Hash-based token (SHA-256(secret+projectId))**: leaks the secret if leaked, harder to migrate, rotation story unnecessary for a token with no expiry in MVP.

---

## R-08. Authentication

**Decision**
- **ASP.NET Core Identity + cookie auth** with email + password. `AddIdentity<IdentityUser, IdentityRole>()` + `AddEntityFrameworkStores<AppDbContext>()`.
- Identity UI scaffolded minimally (login + register + logout), served from the React app via a dedicated `/auth/*` route group.
- **Tenancy** is modelled as an `OwnerId` foreign key on every project-scoped table. The current user is resolved from `HttpContext.User` and a `IQueryFilter` in `AppDbContext` automatically restricts queries to `OwnerId == currentUserId`.
- No MFA, no password reset emails in MVP (the "forgot password" button can show a "contact support" stub).

**Rationale**
- The spec requires "authenticated user" for the dashboard and "no auth" for the public page. Cookie auth is the standard for an SPA + same-origin API and requires zero extra infrastructure (no Redis, no JWT key management, no refresh-token rotation).
- ASP.NET Identity is in the box, integrates with the existing `AppDbContext`, and gives us tenant scoping (FR-024) for free via `IdentityUser.Id` as the `OwnerId` foreign key.
- The spec's Assumption §3 says "a minimum viable sign-in is enough". Cookie + email/password is the lowest-friction option that does not paint us into a corner: migrating to OIDC/Azure AD/Auth0 later is a 1-day swap of the auth scheme; the `[Authorize]` attributes and the public-page carve-out remain unchanged.

**Alternatives considered**
- **No auth at all (single-tenant demo)**: explicitly rejected — FR-026 and SC-006 require tenant isolation even at MVP, and skipping auth makes the P3 multi-tenant story a rewrite.
- **JWT bearer from a third-party IdP (Auth0, Clerk)**: premature; the spec assumes self-hosted; cost is fine but adds a network dependency the MVP can avoid.
- **Magic-link only (passwordless email)**: rejected — requires SMTP credentials or a transactional email provider on day 1, which is a separate vendor evaluation.
- **IdentityServer / Duende**: rejected — brings an OIDC server we don't need; `AddIdentity` is the right surface for an MVP.

---

## R-09. Tests

**Decision**
- **Backend tests** under `app/tests/backend/`:
  - `app/tests/backend/Unit/` — pure logic: `ProjectStateTransitionTests` (the only place real domain logic lives), `ShareTokenTests`, `ValidatorTests`.
  - `app/tests/backend/Integration/` — `WebApplicationFactory<Program>` with **Testcontainers** for Postgres + MinIO. Hits the real `Program.cs`, real Postgres schema, real MinIO container, and a **real Python converter sidecar** (one container started in `IAsyncLifetime`, with a tiny test IFC committed to the test project). Asserts the full `upload → upload-received → processing → ready-to-publish` round-trip and the `publish → GET /s/{token}` round-trip.
  - `app/tests/backend/Contract/` — JSON-schema-style assertions on the API responses consumed by the React app (snapshot tests).
- **Frontend tests** under `app/tests/frontend/`:
  - `app/tests/frontend/Unit/` — Vitest + React Testing Library for the upload form, the share dialog, the `<model-viewer>` wrapper component.
  - `app/tests/frontend/E2E/` — Playwright: one happy-path e2e (open the public URL in a headless browser, assert the `<model-viewer>` element renders and the AR button is present on a UA-string spoofed Android).
- **The conversion boundary is tested against a real IfcOpenShell sidecar** (Testcontainer in the integration fixture). The `IModelConverter` interface exists precisely so unit tests of handlers can substitute a `FakeModelConverter` that returns canned bytes — that is the only place the converter is mocked. The "does the real `IfcConvert` produce a valid GLB" test runs once per CI on a representative 200 KB sample IFC.
- xUnit + FluentAssertions for backend; Vitest for frontend.

**Rationale**
- The constitution's Principle IV mandates `app/tests/{backend,frontend}/` separation. The pyramid above is the smallest one that gives confidence in the only two non-trivial pieces: the state machine and the conversion round-trip.
- xUnit is the de-facto .NET test framework; FluentAssertions is the readable assertion library the community has standardised on.
- Testcontainers is the only way to test MinIO access policies, presigned URL expiry, and the Postgres `FOR UPDATE SKIP LOCKED` claim behaviour without an in-memory fake that drifts from production.

**Alternatives considered**
- **NUnit + Moq**: equivalent, but xUnit's `[Fact]`/`[Theory]` is more idiomatic for ASP.NET Core 9 and avoids Moq's expression-tree tax.
- **No integration tests, all unit tests with NSubstitute**: rejected — leaves the GLB-generation and presigned-URL paths untested; FR-007 (asynchronous conversion) and FR-015 (public reachability) can only be asserted end-to-end.
- **Spin up the full docker-compose in CI for every PR**: rejected — too slow, too flaky; only the e2e Playwright test needs the full stack, and even that is gated on main.

---

## R-10. Docker compose topology

**Decision**
- **Five services** for MVP:
  1. `postgres` (`postgres:16-alpine`)
  2. `minio` (`minio/minio:latest`)
  3. `backend` (rewrite Dockerfile to a multi-stage .NET 9 build; do not embed IfcConvert)
  4. `frontend` (Node 20 → nginx:alpine)
  5. `converter` (Python sidecar; expose `:8080` for the .NET `IModelConverter` HTTP client)
- **Drop `nginx`** from the dev compose: the frontend dev server (Vite, port 3000) and backend (port 5000) talk directly to each other via CORS as they already do. Reintroduce `nginx` only for the production compose (separate file, `docker-compose.prod.yml`) once we have a real domain and TLS.
- **Keep the converter separate.** Do not merge it into the backend.

**Rationale**
- The `converter` image is `python:3.11-slim` + the ~80 MB `IfcConvert` Linux64 binary + `opencascade` libs. The backend image is `mcr.microsoft.com/dotnet/aspnet:9.0` (~120 MB) plus the app. Merging them would push the backend image to ~700 MB, force the API process to live with a 600 MB native binary whose failure modes are a different operational class, and couple the conversion upgrade path to the API release cycle — exactly the wrong direction for FR-010/FR-029.
- The current docker-compose is already five services plus nginx; the minimal set is "drop nginx from dev", not "merge converter into backend". The `depends_on: service_healthy` chain already in place is the right startup ordering.

**Alternatives considered**
- **Merge the converter into the backend image**: rejected per rationale above; also forces every backend redeploy to re-pull the IfcConvert binary, which is the slowest dependency to download.
- **Tilt/Skaffold dev loop**: out of scope for MVP; revisit if the team grows past two developers.

---

## Cross-cutting summary

| Concern | Choice |
|---|---|
| Framework | ASP.NET Core 9 single project, folder-based layers |
| In-process messaging | MediatR 14.x (commands/queries only) |
| Logging | Serilog with `LogContext` correlation ID |
| DB | PostgreSQL 16 + EF Core 9 (Npgsql provider) |
| Object storage | MinIO, 4 buckets: `ifc-files`, `glb-files`, `thumbnails`, `qrcodes` |
| Queue | Postgres `FOR UPDATE SKIP LOCKED` (cheapest durable) |
| Conversion tool | IfcOpenShell `IfcConvert` CLI in a Python sidecar |
| QR | QRCoder 1.8.0, `PngByteQRCode` |
| Frontend viewer | `<model-viewer>` (Google web component) |
| Public token | `Guid.NewGuid()` on a separate `ShareLinks` row |
| Auth | ASP.NET Core Identity + cookies |
| Tests | xUnit + FluentAssertions + Testcontainers + Playwright e2e |
| Docker services | postgres, minio, backend, frontend, converter (5) |

---

## Spec coverage check

| FR range | Where it lands |
|---|---|
| FR-001…FR-005 (project CRUD + upload + validation) | `Application/Projects/Commands/CreateProjectHandler.cs` + ASP.NET Identity |
| FR-006 (state machine) | `Domain/Project.TransitionTo(...)` + handler-level guard |
| FR-007/FR-008 (async conversion, thumbnail) | Python sidecar + `IModelConverter` |
| FR-009/FR-010/FR-029/FR-030 (failure handling, abstraction, future formats) | `IModelConverter` + `Status='Failed'` + reason text |
| FR-011…FR-014 (publish, idempotent, unguessable token) | `ShareLinks` table, `Guid` token, idempotent insert |
| FR-015 (public no-auth) | `[AllowAnonymous]` on `/s/{token}` page |
| FR-016…FR-020 (viewer, thumbnail, AR, no-BIM) | `<model-viewer>` |
| FR-021…FR-023 (dashboard) | React + Identity cookie |
| FR-024/FR-025/FR-026/SC-006 (tenant isolation) | `OwnerId` FK on every project-scoped row; tenant check in every handler; "not found" for cross-tenant |
| FR-027/FR-028 (structured logs, user-readable errors) | Serilog with `LogContext.PushProperty("CorrelationId", ...)`; ProblemDetails responses |
| FR-031…FR-033 (non-goals) | product copy review + AR-attribute-only viewer + extension whitelist = `.ifc` |

**All 33 functional requirements have a known implementation path. Zero open `NEEDS CLARIFICATION` markers remain.**
