<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at:
`specs/001-ifc-mvp-platform/plan.md`

**Active correction (2026-06-10)**: iPhone Quick Look AR fix — remove MinIO, local `/data` storage, mandatory USDZ via `usd_from_gltf`, direct file serving without redirects. See plan.md **Correction Scope**.

Supporting artifacts (read in this order when implementing a task):
- `specs/001-ifc-mvp-platform/spec.md` — original WHAT/WHY (partially superseded by correction scope in plan.md)
- `specs/001-ifc-mvp-platform/research.md` — technology decisions (R-11…R-17 for correction; earlier R-01…R-10 where not superseded)
- `specs/001-ifc-mvp-platform/data-model.md` — entities, validation rules, state machine
- `specs/001-ifc-mvp-platform/contracts/openapi.md` — HTTP API contract (frontend + converter sidecar)
- `specs/001-ifc-mvp-platform/quickstart.md` — end-to-end validation scenarios
- `specs/001-ifc-mvp-platform/adr-001-frontend-separation.md` — architectural decisions on frontend separation of concerns

Active feature: `001-ifc-mvp-platform` (Arch3DAR — IFC-to-AR 3D Sharing MVP).
Repository layout: `app/{backend,frontend,converter,tests}/` (do not change).
Constitution: `.specify/memory/constitution.md` (v1.0.0 — MVP-pragmatism, YAGNI, single responsibility).
<!-- SPECKIT END -->
