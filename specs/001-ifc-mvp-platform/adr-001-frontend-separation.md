# Architectural Decision Record: Frontend Separation of Concerns

**Date**: 2026-06-10
**Status**: Decided / Implemented
**Context**: Issue #001-ifc-mvp-platform

## Problem

The frontend administrative application was mixing three distinct responsibilities:
1. **Administration**: Dashboard, upload, project management
2. **3D Viewing**: Embedded `<model-viewer>` in ProjectDetailPage
3. **AR**: Augmented Reality capabilities embedded in the admin interface

Additionally, a critical bug was identified: `ProjectDetailPage.tsx` was using `project.thumbnailUrl` as the `glbUrl` for the 3D viewer, meaning the viewer was receiving an image instead of a 3D model.

## Analysis

### What the MVP Spec Says (FR-016 to FR-023)

The specification requires:
- **FR-016**: Public page MUST render 3D model with orbit/zoom/pan/fullscreen
- **FR-017**: Public page MUST show thumbnail preview while 3D model loads
- **FR-018**: Public page MUST offer AR on supported devices
- **FR-022**: Admin detail view MUST show "generated thumbnail" and "generated 3D asset"

### Interpretation

- **Public Page (SharePage)**: Correctly implements FR-016/FR-017/FR-018 with `<model-viewer>` and AR. ✅
- **Admin Detail Page (ProjectDetailPage)**: FR-022 requires showing evidence of the 3D asset, not necessarily embedding an interactive viewer. The admin interface should focus on **management** (status, links, QR codes) while the **public page** handles **viewing and AR**.

### Bug: thumbnailUrl as glbUrl

```typescript
// BEFORE (bug):
const glbPresignedUrl = project.thumbnailUrl; // ❌ Image passed as 3D model
```

The backend `ProjectDto` intentionally does NOT include `glbUrl` for admin endpoints (security/least-privilege). The public page receives `glbUrl` via `PublicShareDto`. The admin detail page was incorrectly trying to use the thumbnail as a 3D model.

## Decision

### P0 - Immediate Fixes (Implemented)

1. **Remove `<ModelViewer>` from `ProjectDetailPage`**
   - Admin detail page now shows: thumbnail, status, publish button, and share link/QR code
   - No 3D viewer or AR in the admin interface

2. **Remove the `glbPresignedUrl = thumbnailUrl` bug**
   - The variable no longer exists
   - The admin page does not attempt to render 3D models

3. **Keep `<ModelViewer>` and `useArCapability` in `SharePage`**
   - The public page remains the sole location for 3D viewing and AR
   - This respects the separation of concerns

### P1 - Format Support (Deferred)

The user requested support for multiple formats (SKP, RVT, DWG, DXF, DAE, STL, OBJ).

**Decision**: Keep `.ifc` only in the MVP.

**Rationale**: The spec explicitly states:
- **FR-033**: "The MVP MUST NOT support multiple input formats. Only `.ifc` is accepted."
- **FR-029/FR-030**: The architecture (via `IModelConverter` abstraction) is already prepared for future formats, but the MVP implements only IFC.

The `DropZone` component correctly enforces `.ifc` only. This is not a bug — it is spec compliance.

### P2 - Public Viewer Separation (Future)

The user suggested creating a separate public viewer application (e.g., `viewer.arch3d.com` or `/visualizar/:token`).

**Decision**: Defer to post-MVP.

**Rationale**: For the MVP, the `SharePage` route (`/s/:token`) serves as the public viewer. It is:
- Unguessable (FR-014)
- No-auth required (FR-015)
- Has 3D viewer + AR (FR-016 to FR-019)

A separate application would add deployment complexity without improving MVP outcomes. The current architecture allows extracting the SharePage into a standalone app later without changing the backend API.

## Consequences

### Positive
- **Clear separation**: Admin = management, Public = viewing + AR
- **No broken 3D viewer in admin**: The thumbnailUrl bug is eliminated
- **Smaller admin bundle**: `@google/model-viewer` is still in dependencies (used by SharePage), but the admin pages don't load it
- **Simpler admin interface**: Architects focus on sharing, not testing 3D rendering

### Negative
- **Admin cannot preview 3D before sharing**: The architect must publish and open the public link to verify the 3D model. This is acceptable for MVP — the thumbnail provides visual confirmation.
- **Future format support requires backend work**: When SKP/RVT/etc. are added, the `IModelConverter` abstraction and the `DropZone` will need updates together.

## Implementation Notes

### Files Changed
- `app/frontend/src/pages/ProjectDetailPage.tsx`: Removed `ModelViewer` import and usage; removed `glbPresignedUrl` bug; added "Show share link" button for published projects
- `app/frontend/src/__tests__/ProjectDetailPage.test.tsx`: New tests verifying admin page shows thumbnail but NOT 3D viewer

### Files NOT Changed
- `app/frontend/src/pages/SharePage.tsx`: Unchanged — public viewer remains correct
- `app/frontend/src/components/ModelViewer.tsx`: Unchanged — still used by SharePage
- `app/frontend/src/auth/useArCapability.ts`: Unchanged — still used by SharePage
- `app/frontend/src/components/DropZone.tsx`: Unchanged — `.ifc` restriction is spec-compliant
- `app/frontend/package.json`: Unchanged — `@google/model-viewer` is needed for SharePage

## Compliance Check

| Principle | Status | Evidence |
|---|---|---|
| I. Clean Code & MVP Pragmatism | ✅ Pass | Removed premature 3D viewer from admin. YAGNI: admin doesn't need to render 3D. |
| II. Meaningful Naming | ✅ Pass | `SharePage` = public viewer, `ProjectDetailPage` = admin detail. Clear separation. |
| III. Single Responsibility | ✅ Pass | Admin page manages projects. Public page renders 3D. Each has one job. |
| IV. Tests Mirror Structure | ✅ Pass | Added `ProjectDetailPage.test.tsx` with 4 tests covering the fix. |
| V. Self-Documenting | ✅ Pass | No comments needed — the code structure shows the separation. |
