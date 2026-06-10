# Feature Specification: Arch3DAR — IFC-to-AR 3D Sharing MVP

**Feature Branch**: `001-ifc-mvp-platform`
**Created**: 2026-06-09
**Status**: Draft
**Input**: User description: "Plataforma SaaS de compartilhamento de modelos 3D para arquitetura, interiores e móveis planejados utilizando IFC como formato de entrada e GLB como formato de visualização e Realidade Aumentada."

> **Product positioning**: Arch3DAR is **not** a BIM platform, **not** a coordination tool, and **not** an engineering suite. It is a SaaS that lets architects, interior designers, and custom-furniture manufacturers share a single 3D model with their client through a public link and AR — solving the "I cannot see the piece in my real room" problem.

---

## User Scenarios & Testing *(mandatory)*

User stories are ordered by dependency and business value. The MVP only delivers value if stories P1–P3 all work end-to-end.

### User Story 1 — Architect publishes a model and shares a public link (Priority: P1)

An architect (or interior designer / furniture maker) creates a project, uploads a single `.ifc` file exported from SketchUp/Revit/AutoCAD/ArchiCAD/Blender, waits for the system to process it, then publishes the project and receives a public URL plus a QR code to send to the client.

**Why this priority**: This is the entire value proposition. Without upload + conversion + share, the product does not exist. Every other story is downstream of this one.

**Independent Test**: A new project is created, a sample `.ifc` is uploaded, conversion completes (status = "converted"), publish returns a public URL and a QR code image, both are reachable.

**Acceptance Scenarios**:

1. **Given** an authenticated user with no projects, **When** they create a project named "Living Room Sofa" and upload a valid `.ifc` file (≤ configured size limit), **Then** the system stores the original file, transitions the project to "processing", and starts conversion asynchronously.
2. **Given** a project whose conversion finished successfully, **When** the user clicks "Publish", **Then** the system returns a public URL and a QR code image pointing to that URL, and transitions the project to "published".
3. **Given** an upload of a file whose extension is not `.ifc` or whose size exceeds the configured limit, **When** the user submits it, **Then** the system rejects the upload before persisting any file and returns a clear, user-readable error.
4. **Given** a conversion that fails internally, **When** the system detects the failure, **Then** the project status becomes "failed" with a user-readable reason, and no public link is generated.
5. **Given** an already-published project, **When** the user clicks "Publish" again, **Then** the same public link and QR code are returned (idempotent) without creating a second one.

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

### User Story 4 — Architect manages projects from a dashboard (Priority: P2)

The architect logs in to a dashboard that lists their projects with key information, lets them create a new project, upload a file, and see status + thumbnail while conversion runs. They can open a project detail view to see generated artifacts and trigger publishing.

**Why this priority**: UX glue around P1. Without it the architect would have to use raw API calls. It can be reduced for the very first market test (one project, one share) but is needed before paying customers use the product.

**Independent Test**: Sign in, see the dashboard, create + upload a new project, see it appear with status "processing" → "ready to publish", open detail, click publish, see link + QR.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they open the dashboard, **Then** they see a list of their projects with name, creation date, current status, and a thumbnail (when available).
2. **Given** the dashboard, **When** the user clicks "New project", **Then** they are taken to a creation flow where they can name the project, describe it, optionally add a client name, and upload an `.ifc` file via drag-and-drop or file picker.
3. **Given** the upload is in progress, **When** the user watches the UI, **Then** a progress indicator reflects the upload state, and once the upload finishes the UI switches to "processing".
4. **Given** a project whose status is "ready to publish" (conversion succeeded), **When** the user opens the project detail, **Then** the detail view shows the thumbnail, the generated 3D asset, and a "Publish" action.
5. **Given** a project whose status is "failed", **When** the user opens the project detail, **Then** a user-readable error reason is shown and the project can be retried by uploading a new file (deleting the old one is not required for MVP).

---

### User Story 5 — Multi-tenancy / data isolation (Priority: P3)

Projects, files, and public links are scoped to a tenant (the architect's account / organization). One tenant cannot see or modify another tenant's data. Public links expose only what is strictly necessary to render the model — no internal IDs or tenant metadata are leaked.

**Why this priority**: Required for the product to be sold to more than one customer. Out of scope for the very first "one architect shares with one client" validation, but architecture must not block it.

**Independent Test**: As Tenant A, create and publish a project. As Tenant B, attempt to read the project via API or guess the public URL — the response is "not found" and no file is served.

**Acceptance Scenarios**:

1. **Given** a user from Tenant A, **When** they list projects, **Then** they only see projects belonging to Tenant A.
2. **Given** a public link for Tenant A, **When** an unauthenticated visitor opens it, **Then** the rendered page contains only the project's name, its 3D model, and a thumbnail — no tenant ID, internal IDs, or other tenants' data.
3. **Given** a user from Tenant B, **When** they attempt to read or modify a project ID belonging to Tenant A, **Then** the system responds as if the project does not exist (no enumeration leak).

---

### Edge Cases

- **Oversized file**: a user uploads an `.ifc` larger than the configured limit. The upload must be rejected before the file is fully transferred (or buffered) and the user must see a clear "file too large" message.
- **Wrong file type**: a user uploads a `.pdf` or `.jpg` renamed to `.ifc`. The system must validate the file signature (not just the extension) and reject the upload with a clear message.
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

- **FR-001**: The system MUST let an authenticated user create a project with a name, optional description, and optional client label.
- **FR-002**: The system MUST let an authenticated user upload a single `.ifc` file as part of creating or updating a project.
- **FR-003**: The system MUST validate that the uploaded file is an IFC file (by content signature, not only by extension) and reject invalid files with a user-readable message before persisting them.
- **FR-004**: The system MUST enforce a maximum file size per upload and reject oversized uploads with a clear message.
- **FR-005**: The system MUST persist the original uploaded file in durable object storage, scoped to the project.
- **FR-006**: The system MUST track the project lifecycle through these states: `upload-received`, `processing`, `ready-to-publish`, `published`, `failed`. Transitions are monotonic except for `processing → failed`.

**Conversion**

- **FR-007**: The system MUST convert each uploaded `.ifc` file into a 3D model in a web- and AR-friendly format (`glb`) asynchronously, without blocking the upload HTTP request.
- **FR-008**: The system MUST generate a thumbnail preview image (web-friendly format) from the model during conversion.
- **FR-009**: The system MUST handle conversion failures by transitioning the project to `failed` with a user-readable reason and MUST NOT generate a public link for a failed project.
- **FR-010**: The conversion pipeline MUST be abstracted behind a single internal interface so that future input formats (SKP, RVT, DWG, DXF, OBJ, STL, DAE, FBX) can be added without changing upload or share flows. The MVP MUST NOT implement those formats — only the abstraction.

**Sharing**

- **FR-011**: The system MUST let an authenticated user publish a project whose state is `ready-to-publish` and generate a public URL plus a QR code image in response.
- **FR-012**: The system MUST generate the QR code from the public URL automatically (no manual QR upload).
- **FR-013**: The system MUST make publishing idempotent: publishing an already-published project returns the same link/QR, it does not create a second one.
- **FR-014**: Public URLs MUST be non-sequential and unguessable (e.g., GUID/ULID or equivalent entropy) and MUST NOT expose internal database IDs.
- **FR-015**: The public page MUST be reachable without authentication and MUST NOT require any account to view the 3D model or thumbnail.

**3D viewing & AR**

- **FR-016**: The public page MUST render the 3D model with orbit, zoom, pan, and fullscreen controls.
- **FR-017**: The public page MUST show a thumbnail preview while the 3D model is loading.
- **FR-018**: The public page MUST offer an "Open in AR" / "View in your space" action on supported devices that hands the model off to the device's native AR experience at real-world scale.
- **FR-019**: On devices without AR capability the public page MUST degrade gracefully: the 3D viewer must remain fully functional and the AR option MUST be hidden or clearly disabled — never shown as a broken button.
- **FR-020**: The 3D viewer MUST NOT include any BIM/engineering features (no properties tree, no element metadata, no clash detection, no measurement tools). It is a viewer, not a CAD tool.

**Dashboard**

- **FR-021**: An authenticated user MUST be able to list their projects, with name, creation date, current status, and thumbnail.
- **FR-022**: An authenticated user MUST be able to open a project detail view showing its current state, the generated thumbnail, and the generated 3D asset.
- **FR-023**: An authenticated user MUST be able to copy the public link and download/display the QR code from the project detail or share view.

**Security & isolation**

- **FR-024**: Projects, files, and links MUST be scoped to a tenant. A user MUST NOT be able to read or modify another tenant's data.
- **FR-025**: The public page MUST expose only the minimum data required to render the model and thumbnail; it MUST NOT expose internal IDs, tenant IDs, or any other tenant's data.
- **FR-026**: The system MUST validate that an authenticated API request is allowed to act on a given project before returning or mutating it.

**Observability & errors**

- **FR-027**: The system MUST emit structured logs for upload, conversion lifecycle events, publishing, and errors, correlated by a request / job correlation ID.
- **FR-028**: The system MUST surface user-readable error messages to dashboard and public page users, and MUST NOT leak stack traces or internal exception details in those messages.

**Extensibility (architecture only — no implementation of additional formats in MVP)**

- **FR-029**: The conversion pipeline MUST be implemented as an abstraction that accepts a single source model and produces a web/AR-ready output plus a thumbnail. Adding a new input format MUST require implementing a new converter and registering it — no change to the upload, share, or viewer code.
- **FR-030**: The MVP MUST support only IFC. Other formats are explicitly out of scope for implementation but the architecture MUST NOT block them.

**Explicit non-goals (to prevent scope creep)**

- **FR-031**: The product MUST NOT present itself as a BIM platform, BIM collaboration tool, BIM coordination tool, BIM metadata manager, or engineering suite. Any UI, copy, docs, or marketing surfaces generated by this product MUST avoid those terms and use neutral wording (e.g., "3D model", "architecture", "interior design", "custom furniture").
- **FR-032**: The MVP MUST NOT support editing, version control, comments, annotations, or multi-user collaboration on the 3D model.
- **FR-033**: The MVP MUST NOT support multiple input formats. Only `.ifc` is accepted.

### Key Entities *(include if feature involves data)*

- **Project**: a single 3D sharing unit. Belongs to one tenant. Has a name, optional description, optional client label, current status, and timestamps (created, updated, published). One project has zero or one source file and zero or one generated 3D asset.
- **ProjectFile**: the durable, stored artifacts associated with a project — the original uploaded file, the generated 3D model, and the generated thumbnail. Persisted in object storage, referenced from the project record by storage path.
- **ShareLink**: a public, non-sequential, unguessable token bound to a published project. Resolves to a public viewer page. Has a creation timestamp and the project it points to. The QR code image is derived from this token's public URL.

---

## Success Criteria *(mandatory)*

Outcomes are measured from the architect's and client's perspective, not from system internals.

### Measurable Outcomes

- **SC-001**: An architect can go from "open dashboard" to "client has a working public link" in under 5 minutes for a typical 50 MB `.ifc` file on a standard broadband connection (≤ 200 ms latency, ≥ 10 Mbps up), measured from the moment they click "New project" to the moment the public page renders the 3D model on the client's phone.
- **SC-002**: 100% of valid `.ifc` uploads of size ≤ 100 MB complete conversion (no project left stuck in `processing` beyond the configured timeout) on the first attempt in a healthy environment.
- **SC-003**: 100% of published projects' public links load in a modern mobile browser (Chrome on Android 10+ and Safari on iOS 15+) in under 10 seconds on a 4G connection, showing the thumbnail first and the 3D model second.
- **SC-004**: 100% of public pages on supported AR-capable mobile devices offer a working "Open in AR" handoff that places the model in the real environment at real-world scale; on unsupported devices the option is hidden and the 3D viewer still works.
- **SC-005**: Public links are unguessable: guessing 1,000,000 random URLs has effectively 0% chance of returning a valid public page.
- **SC-006**: 100% of attempts by a user from Tenant B to read, modify, or guess a project belonging to Tenant A return a "not found" response with no data leakage.
- **SC-007**: The end-to-end flow (create → upload → conversion → publish → public page loads → AR handoff) can be demonstrated and passes automated end-to-end tests on a clean local environment using only the documented setup commands.
- **SC-008**: The product surfaces in UI, copy, documentation, and logs use the term "3D model" / "architecture / interior / furniture" and contain zero occurrences of "BIM platform", "BIM collaboration", "BIM coordination", "BIM metadata", "BIM management", or "BIM engineering".

---

## Assumptions

- **Users have stable broadband**. Upload, conversion, and viewing assume a connection that can sustain tens of MB transfers; the system is not designed for offline use.
- **One model per project in MVP**. A project carries a single source file. Multi-file or multi-revision workflows are out of scope for MVP.
- **Authentication is required for the dashboard, not for the public page**. Tenant boundaries exist for paying customers, but the MVP does not need a full auth system UI to validate the market — a minimum viable sign-in is enough.
- **IfcOpenShell / IfcConvert is available in the conversion environment**. The conversion worker has the tooling required to turn IFC into GLB. The MVP does not need to convert other formats.
- **Object storage is available in the environment**. Files (uploaded IFC, generated GLB, thumbnail, QR code) are stored in durable object storage, not on local disk.
- **The conversion worker is separate from the HTTP API**. Conversion runs out-of-band and does not block the upload response.
- **Mobile devices are the primary AR target**. The desktop experience is 3D-viewer only; AR is mobile-first.
- **The "project" lifecycle is a simple state machine**. No complex workflows (review, approval, scheduled publish, expiry) are in scope for MVP.
- **The current repository's existing code is treated as a starting point that may be substantially rewritten**. The MVP scope is narrow and the product is repositioned away from "BIM viewer"; significant code paths in the existing repo may not survive the migration. Specific GAP analysis and migration plan are produced by downstream planning, not by this spec.
