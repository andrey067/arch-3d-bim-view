# Feature Specification: Arch3DAR — IFC/SketchUp-to-AR 3D Sharing MVP

**Feature Branch**: `001-ifc-mvp-platform`
**Created**: 2026-06-09
**Status**: Draft
**Input**: User description: "Plataforma de compartilhamento de modelos 3D para arquitetura, interiores e móveis planejados com upload de `.ifc` ou `.skp`, conversão para visualização Web e Realidade Aumentada (Android + iPhone)."

> **Product positioning**: Arch3DAR is **not** a BIM platform, **not** a coordination tool, and **not** an engineering suite. It lets architects, interior designers, and custom-furniture manufacturers share a single 3D model with their client through a public link and AR — solving the "I cannot see the piece in my real room" problem.

> **MVP scope (clarified)**: Simplified single-tenant flow — upload page + public viewer, **no authentication**, **no dashboard**, **local filesystem storage**, **no object storage / MinIO**. Accepts **`.ifc`**, **`.dae`** (SketchUp Collada export), and **`.obj`** in the same release. **Direct `.skp` upload is not supported** — SketchUp users MUST export to Collada (`.dae`) first. Focus: geometry, materials, textures, web 3D viewer, and AR — **not** IFC spatial tree, properties, classification, or BIM metadata.

---

## Clarifications

### Session 2026-06-10

- Q: Qual escopo rege o spec — correção IFC-only, SpecDrive completo, ou faseado? → A: **SpecDrive sobre a correção** — MVP simplificado (sem auth), IFC + SKP no mesmo release.
- Q: Qual pipeline primário para conversão SKP? → A: **Blender headless: SKP → GLB direto** (import SKP nativo + export glTF 2.0; sem DAE intermediário, sem Assimp).
- Q: Qual layout de armazenamento no disco local? → A: **`/data/projects/{projectId}/`** — conforme correção ativa (não `/uploads`).
- Q: Qual formato padrão do thumbnail? → A: **`thumbnail.webp`** — WebP gerado via Blender headless render.
- Q: Como organizar conversores no Docker Compose? → A: **Sidecar único `converter`** — IfcOpenShell + Blender + USDZ + thumbnail num container Python; serviços: postgres, backend, converter, frontend.
- Q: Qual estratégia de conversão SketchUp no MVP, dado que Blender oficial não importa `.skp` nativamente? → A: **Upload DAE/OBJ para fluxo SketchUp** — usuários exportam Collada (`.dae`, primário) ou Wavefront (`.obj`) do SketchUp; conversão via Blender headless import nativo Collada/OBJ → GLB. Upload direto de `.skp` fora de escopo; sem addon pago nem pipeline ODA.
- Q: Como orientar usuários SketchUp na página de upload? → A: **Instruções proeminentes na página** — passos de exportação (File → Export → 3D Model → Collada `.dae`) visíveis no upload, junto à lista de formatos aceitos (`.ifc`, `.dae`, `.obj`).
- Q: Onde bloquear upload de `.skp`? → A: **Cliente + servidor** — file picker `accept` lista apenas `.ifc`, `.dae`, `.obj`; servidor rejeita `.skp` com instruções de exportação Collada se contornado.

---

## User Scenarios & Testing *(mandatory)*

User stories are ordered by dependency and business value. The MVP only delivers value if stories P1–P3 all work end-to-end.

### User Story 1 — Architect uploads a model and receives a public link (Priority: P1)

An architect (or interior designer / furniture maker) opens the upload page, submits a single `.ifc`, `.dae`, or `.obj` file (from SketchUp via Collada export, Revit, AutoCAD, ArchiCAD, Blender, etc.), waits for automatic conversion, and receives a public URL plus a QR code to send to the client. SketchUp users export **File → Export → 3D Model → Collada (.dae)** before uploading. No login is required.

**Why this priority**: This is the entire value proposition. Without upload + conversion + share, the product does not exist. Every other story is downstream of this one.

**Independent Test**: Upload a sample `.ifc` or `.dae`, conversion completes (status = ready), the response includes a public URL and QR code, both are reachable.

**Acceptance Scenarios**:

1. **Given** the upload page, **When** the user submits a valid `.ifc`, `.dae`, or `.obj` file (≤ configured size limit), **Then** the system stores the original file on local disk, transitions the project to "processing", and starts conversion without blocking the upload response.
2. **Given** a project whose conversion finished successfully, **When** conversion completes, **Then** the system returns (or displays) a public URL and a QR code image pointing to that URL.
3. **Given** an upload whose extension is not `.ifc`, `.dae`, or `.obj` (including `.skp`), or whose size exceeds the configured limit, **When** the user submits it, **Then** the system rejects the upload before persisting any file and returns a clear, user-readable error (for `.skp`, the message MUST direct the user to export Collada from SketchUp).
4. **Given** a conversion that fails internally, **When** the system detects the failure, **Then** the project status becomes "failed" with a user-readable reason, and no public link is generated.
5. **Given** a valid `.dae` or `.obj` upload exported from SketchUp with materials and textures, **When** conversion completes, **Then** the generated GLB preserves visible materials and textures in the web viewer (best-effort; exact fidelity is not guaranteed for every SketchUp feature).

---

### User Story 2 — Client opens the public link and views the 3D model (Priority: P1)

The client (end customer) receives the public URL (e.g., via WhatsApp, email, or printed QR code), opens it on any modern browser (desktop or mobile) without logging in, and sees a 3D model of the piece. They can orbit, zoom, pan, and go fullscreen. A thumbnail preview is shown while the 3D asset loads.

**Why this priority**: Without client-side viewing, the link the architect shares is useless. This is half of the deliverable that makes the product worth paying for.

**Independent Test**: Open the public URL in an incognito window (no auth), wait for the GLB to load, and confirm orbit/zoom/pan/fullscreen all work and a thumbnail was visible before the 3D model finished loading.

**Acceptance Scenarios**:

1. **Given** a published project, **When** an unauthenticated user opens its public URL, **Then** the page loads without requiring login, displays a thumbnail preview, then renders the 3D model in an interactive viewer.
2. **Given** the 3D viewer is loaded, **When** the user drags / scrolls / pinches, **Then** the camera orbits, zooms, and pans around the model respectively.
3. **Given** the viewer, **When** the user activates fullscreen mode, **Then** the viewer fills the screen and a way to exit fullscreen is provided.
4. **Given** a public URL for a project that is still processing, **When** an unauthenticated user opens it, **Then** the page shows the current status (e.g., "processing") with a clear explanation instead of a broken viewer.
5. **Given** a public URL for a non-existent or unpublished project, **When** a user opens it, **Then** a friendly "not found / not available" page is shown — no internal data is leaked.

---

### User Story 3 — Client places the model in their real environment via AR (Priority: P1)

On a mobile device, the client taps an "View in your space" / "AR" button on the public page and the system launches the device's native AR experience, allowing the client to position the model at real-world scale inside their own room.

**Why this priority**: AR is the unique differentiator. It is the reason the client cares. Without it, the product competes on price with every static image gallery.

**Independent Test**: Open the public URL on a recent Android Chrome, tap the AR button, and confirm a native AR session opens with the model anchored in the real environment. On iOS Safari the page should at minimum surface the appropriate intent for the platform's native AR viewer.

**Acceptance Scenarios**:

1. **Given** a supported Android device with ARCore available, **When** the user taps the AR button on the public page, **Then** the system launches a native AR session that places the model at real-world scale in the user's environment.
2. **Given** a supported iOS device, **When** the user taps the AR button, **Then** the system hands off to the platform's native AR viewer with the same model so the user can position it in their space.
3. **Given** a device/browser without AR capability, **When** the user views the public page, **Then** the AR button is either hidden or clearly disabled, and the 3D viewer remains fully usable as a fallback.
4. **Given** the public page is opened on a desktop browser without AR, **When** the user views the page, **Then** the AR option is not shown (no broken/dead button), but the 3D viewer works as in Story 2.

---

### User Story 4 — Architect manages projects from a dashboard *(Out of scope — MVP)*

Deferred. The simplified MVP uses a single upload page; there is no authenticated dashboard, project list, or publish step. Conversion success automatically yields a shareable link.

---

### User Story 5 — Multi-tenancy / data isolation *(Out of scope — MVP)*

Deferred. The simplified MVP is single-tenant with no authentication. Public links remain unguessable; internal project IDs MUST NOT appear in public URLs.

---

### Edge Cases

- **Oversized file**: a user uploads an `.ifc`, `.dae`, or `.obj` larger than the configured limit. The upload must be rejected before the file is fully transferred (or buffered) and the user must see a clear "file too large" message.
- **Wrong file type**: a user uploads a `.pdf` or `.jpg` renamed to `.ifc`, `.dae`, or `.obj`. The system must validate the file signature (not just the extension) and reject the upload with a clear message.
- **Raw `.skp` upload**: a SketchUp user attempts `.skp` directly (blocked by file picker `accept` on the client; if bypassed, rejected server-side) instead of exporting Collada. The system must reject with a message explaining how to export `.dae` from SketchUp (File → Export → 3D Model → Collada).
- **DAE/OBJ with unsupported SketchUp features**: conversion may succeed with simplified geometry or materials; the user sees a warning or generic "partial conversion" message rather than a silent broken viewer.
- **USDZ generation failure**: iPhone AR requires a valid USDZ; if USDZ generation fails, the project is marked `failed` and AR on iOS is not offered.
- **Conversion never finishes / worker dies**: the project is stuck in "processing". The system must have a timeout/recovery policy that marks the project as "failed" after a configurable deadline and surfaces that to the user.
- **Network interruption mid-upload**: partial files must not be treated as valid uploads; on retry the user should not see a corrupted state.
- **Same public link opened twice simultaneously**: both viewers should work independently.
- **Public link scraped / guessed**: public links are non-sequential and unguessable; an attacker cannot enumerate other projects by guessing IDs.
- **Storage temporarily unavailable**: the system must surface a clear error ("try again later") and not silently drop the user's upload.
- **Project deleted after publish (out of scope for MVP)**: not supported — delete is not in the MVP.

---

## Requirements *(mandatory)*

### Functional Requirements

**Project lifecycle**

- **FR-001**: The system MUST accept a model upload via a public upload page without requiring authentication.
- **FR-001a**: The upload page MUST display prominent SketchUp export instructions (File → Export → 3D Model → Collada `.dae`) and list accepted formats (`.ifc`, `.dae`, `.obj`). The page MUST NOT imply that direct `.skp` upload is supported.
- **FR-001b**: The upload file picker MUST restrict selection via `accept` to `.ifc`, `.dae`, and `.obj` only. If a `.skp` file is submitted despite client restrictions (e.g., API call or picker bypass), the server MUST reject it with the SketchUp Collada export instructions — not a generic "invalid format" message.
- **FR-002**: The system MUST accept a single `.ifc`, `.dae`, or `.obj` file per upload. Direct `.skp` upload is NOT supported.
- **FR-003**: The system MUST validate uploaded files by content signature (not extension alone) and reject invalid files with a user-readable message before persisting them.
- **FR-004**: The system MUST enforce a maximum file size per upload and reject oversized uploads with a clear message.
- **FR-005**: The system MUST persist artifacts under **`/data/projects/{projectId}/`** on local filesystem storage with these filenames: `original.ifc`, `original.dae`, or `original.obj` (matching upload format), `model.glb`, `model.usdz`, and **`thumbnail.webp`**.
- **FR-006**: The system MUST track the project lifecycle through these states: `upload-received`, `processing`, `ready`, `failed`. A successful conversion automatically yields a shareable public link (no separate publish step).

**Conversion**

- **FR-007**: The system MUST convert each uploaded source file into GLB asynchronously, without blocking the upload HTTP response.
- **FR-007a**: IFC uploads MUST be converted via IfcOpenShell (`IfcConvert` or equivalent).
- **FR-007b**: DAE and OBJ uploads (SketchUp workflow) MUST be converted via **Blender headless: Collada/OBJ import → GLB export** (Blender native `import_scene.dae` / `import_scene.obj` + glTF 2.0 export). No third-party SketchUp importer addon and no Assimp in the primary path. Native `.skp` import is explicitly out of scope.
- **FR-007c**: The system MUST generate a USDZ from GLB for iPhone Quick Look AR; USDZ generation failure MUST mark the project `failed`.
- **FR-008**: The system MUST generate a **`thumbnail.webp`** preview image from the converted model during conversion (Blender headless render).
- **FR-009**: The system MUST handle conversion failures by transitioning the project to `failed` with a user-readable reason and MUST NOT generate a public link for a failed project.
- **FR-010**: The conversion pipeline MUST be abstracted behind a single internal interface (`IModelConversionService` or equivalent) that detects input format, runs the appropriate converter, and produces GLB + USDZ + thumbnail. Adding a future format MUST require only a new converter implementation — no change to upload or viewer flows. All conversion tooling (IfcOpenShell, Blender, USDZ, thumbnail) runs in a **single converter sidecar** invoked by the backend.

**Sharing**

- **FR-011**: On successful conversion, the system MUST generate a public URL and a QR code image automatically.
- **FR-012**: The system MUST generate the QR code from the public URL automatically (no manual QR upload).
- **FR-014**: Public URLs MUST be non-sequential and unguessable (e.g., GUID/ULID or equivalent entropy) and MUST NOT expose internal database IDs.
- **FR-015**: The public page MUST be reachable without authentication and MUST NOT require any account to view the 3D model or thumbnail.
- **FR-015a**: Asset URLs (GLB, USDZ, thumbnail) MUST be served directly (HTTP 200, correct Content-Type, no redirects) — required for iPhone Quick Look. Thumbnail Content-Type: `image/webp`.

**3D viewing & AR**

- **FR-016**: The public page MUST render the 3D model with orbit, zoom, pan, fullscreen, and auto-rotate controls.
- **FR-017**: The public page MUST show a thumbnail preview while the 3D model is loading.
- **FR-018**: The public page MUST offer an "Open in AR" / "View in your space" action on supported devices that hands the model off to the device's native AR experience at real-world scale (Scene Viewer on Android, Quick Look on iOS via USDZ).
- **FR-019**: On devices without AR capability the public page MUST degrade gracefully: the 3D viewer must remain fully functional and the AR option MUST be hidden or clearly disabled — never shown as a broken button.
- **FR-020**: The 3D viewer MUST NOT include any BIM/engineering features (no spatial tree, no element properties, no classification, no clash detection, no measurement tools). Focus is geometry, materials, textures, and AR only.

**Dashboard *(out of scope — MVP)***

- **FR-021–FR-023**: Deferred. No authenticated dashboard, project list, or manual publish action in the simplified MVP.

**Security & isolation *(simplified — MVP)***

- **FR-025**: The public page MUST expose only the minimum data required to render the model and thumbnail; it MUST NOT expose internal IDs or stack traces.
- **FR-024, FR-026**: Deferred (multi-tenant auth). Public links remain unguessable as the primary access control.

**Observability & errors**

- **FR-027**: The system MUST emit structured logs for upload, conversion lifecycle events, and errors, correlated by a request / job correlation ID.
- **FR-028**: The system MUST surface user-readable error messages on the upload and public pages, and MUST NOT leak stack traces or internal exception details in those messages.

**Extensibility**

- **FR-029**: The conversion pipeline MUST accept a single source model and produce GLB, USDZ, and thumbnail. New input formats require only a new converter registration.
- **FR-030**: The MVP MUST support `.ifc`, `.dae`, and `.obj` only. Other formats (`.skp`, RVT, DWG, DXF, STL, FBX) are explicitly out of scope but the architecture MUST NOT block them. Future native `.skp` support MAY be added via a new converter registration without changing upload or viewer flows.

**Explicit non-goals (to prevent scope creep)**

- **FR-031**: The product MUST NOT present itself as a BIM platform, BIM collaboration tool, BIM coordination tool, BIM metadata manager, or engineering suite. Any UI, copy, docs, or marketing surfaces generated by this product MUST avoid those terms and use neutral wording (e.g., "3D model", "architecture", "interior design", "custom furniture").
- **FR-032**: The MVP MUST NOT support editing, version control, comments, annotations, or multi-user collaboration on the 3D model.
- **FR-033**: The MVP MUST NOT support authentication, multi-tenancy, object storage (MinIO/S3), or a project dashboard.

### Key Entities *(include if feature involves data)*

- **Project**: a single 3D sharing unit. Has a source format (`ifc` | `dae` | `obj`), current status, public token, and timestamps. One project has one source file and generated artifacts (GLB, USDZ, thumbnail).
- **ProjectFile**: durable artifacts at `/data/projects/{projectId}/` — `original.ifc|dae|obj`, `model.glb`, `model.usdz`, `thumbnail.webp`. Referenced from the project record by relative path within the data volume.
- **ShareLink**: a public, non-sequential, unguessable token bound to a ready project. Resolves to the public viewer page. QR code is derived from this token's public URL.

---

## Success Criteria *(mandatory)*

Outcomes are measured from the architect's and client's perspective, not from system internals.

### Measurable Outcomes

- **SC-001**: A user can go from "open upload page" to "client has a working public link" in under 5 minutes for a typical 50 MB `.ifc` or `.dae` file on standard broadband (≤ 200 ms latency, ≥ 10 Mbps up).
- **SC-002**: 100% of valid `.ifc`, `.dae`, and `.obj` uploads of size ≤ 100 MB complete conversion (no project stuck in `processing` beyond the configured timeout) on the first attempt in a healthy environment.
- **SC-003**: 100% of public links load in a modern mobile browser (Chrome on Android 10+ and Safari on iOS 15+) in under 10 seconds on 4G, showing the thumbnail first and the 3D model second.
- **SC-004**: 100% of public pages on supported AR-capable mobile devices offer a working "Open in AR" handoff (Android Scene Viewer + iOS Quick Look via USDZ); on unsupported devices the option is hidden and the 3D viewer still works.
- **SC-005**: Public links are unguessable: guessing 1,000,000 random URLs has effectively 0% chance of returning a valid public page.
- **SC-006**: *(Deferred — multi-tenant)* Replaced for MVP by SC-005 unguessable tokens.
- **SC-007**: The end-to-end flow (upload → conversion → public page loads → AR handoff) passes automated tests on a clean local environment via `docker compose up`.
- **SC-008**: UI, copy, and docs use "3D model" / "architecture / interior / furniture" and contain zero occurrences of "BIM platform", "BIM collaboration", "BIM coordination", "BIM metadata", "BIM management", or "BIM engineering".
- **SC-009**: DAE/OBJ uploads exported from SketchUp with standard materials and textures render with recognizable colors and textures in the web viewer (best-effort; not pixel-perfect parity with SketchUp desktop).

---

## Assumptions

- **Users have stable broadband**. Upload, conversion, and viewing assume a connection that can sustain tens of MB transfers; the system is not designed for offline use.
- **One model per upload in MVP**. Multi-file or multi-revision workflows are out of scope.
- **No authentication in MVP**. Upload page and public viewer are open; access control is via unguessable public tokens only.
- **IfcOpenShell and Blender headless are available in the conversion environment**. IFC via IfcConvert; DAE/OBJ via Blender native Collada/Wavefront import → GLB (same Blender runtime also used for thumbnail rendering). Stock Blender 4.x does NOT include a native `.skp` importer — SketchUp users export Collada before upload.
- **USDZ via `usd_from_gltf`** (or equivalent) is available for GLB→USDZ conversion required by iPhone Quick Look.
- **Local filesystem storage at `/data/projects/{projectId}/`**. Files live on a shared Docker volume (`project_data:/data`), not in object storage / MinIO / S3.
- **Single converter sidecar in Docker Compose**. One `converter` service (Python) bundles IfcOpenShell, Blender headless, `usd_from_gltf`, and thumbnail rendering. Compose stack: `postgres`, `backend`, `converter`, `frontend` (+ nginx). No separate per-format worker containers.
- **The conversion worker is separate from the HTTP API**. Conversion runs out-of-band and does not block the upload response.
- **Mobile devices are the primary AR target**. Desktop is 3D-viewer only; AR is mobile-first.
- **HTTPS is required for AR** on mobile browsers.
