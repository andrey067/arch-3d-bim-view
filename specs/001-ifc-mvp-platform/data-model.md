# Data Model: Arch3DAR MVP

**Phase**: 1
**Branch**: `001-ifc-mvp-platform`
**Date**: 2026-06-09
**Spec**: `specs/001-ifc-mvp-platform/spec.md`
**Research**: `specs/001-ifc-mvp-platform/research.md`

> The MVP needs four persistent entities: `User` (from ASP.NET Identity), `Project`, `ShareLink`, plus the ASP.NET Identity role/user/claim/role-claim tables. The data model is intentionally narrow — it is exactly the data needed to satisfy the 33 functional requirements and no more.

---

## ER overview

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  IdentityUser│ 1    0 │   Project    │ 1    0 │  ShareLink   │
│  (Identity)  │────────│              │────────│              │
└──────────────┘        └──────────────┘        └──────────────┘
        ▲                       │
        │                       │ 1
        │                       ▼
        │                ┌──────────────┐
        │                │  ProjectFile │  (object keys, not a separate table)
        │                │  (MinIO)     │
        │                └──────────────┘
        │
        └────── owns ────► Project.OwnerId
```

The Project entity holds the storage keys for its artifacts; the bytes live in MinIO. There is no separate `ProjectFile` table — adding one would be premature.

---

## Entities

### `Project` (table `projects`)

The unit of work. One tenant, one source file, one 3D model.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `Id` | `uuid` | PK, default `gen_random_uuid()` | Internal primary key. **Never** exposed in public URLs. |
| `OwnerId` | `uuid` | FK → `AspNetUsers(Id)`, NOT NULL, indexed | Owning tenant. All queries are filtered by `OwnerId` via a global query filter. |
| `Name` | `varchar(200)` | NOT NULL | Project display name. |
| `Description` | `varchar(2000)` | NULL | Optional. |
| `ClientLabel` | `varchar(200)` | NULL | Optional free-form client label (FR-001). |
| `Status` | `varchar(32)` | NOT NULL, default `'UploadReceived'` | One of the `ProjectStatus` enum values (see below). |
| `ErrorMessage` | `varchar(500)` | NULL | User-readable failure reason (FR-009, FR-028). NULL when not failed. |
| `IfcObjectKey` | `varchar(512)` | NULL | MinIO key for the original IFC. NULL only briefly during upload commit. |
| `GlbObjectKey` | `varchar(512)` | NULL | MinIO key for the generated GLB. NULL until conversion completes. |
| `ThumbnailObjectKey` | `varchar(512)` | NULL | MinIO key for the generated thumbnail. NULL until conversion completes. |
| `IfcSizeBytes` | `bigint` | NULL | Uploaded file size in bytes (for quota / display). |
| `ConversionStartedAt` | `timestamptz` | NULL | Set when the worker claims the row. Used by the watchdog. |
| `ConversionDurationMs` | `bigint` | NULL | Wall-clock conversion time. NULL until success. |
| `CreatedAt` | `timestamptz` | NOT NULL, default `now()` | FR-021 sortable timestamp. |
| `UpdatedAt` | `timestamptz` | NOT NULL, default `now()` | Updated on every state transition (FR-027 log correlation). |
| `PublishedAt` | `timestamptz` | NULL | Set once on first publish. |

**Indexes**:
- PK on `Id`.
- `ix_projects_owner_id` on `(OwnerId)`.
- `ix_projects_status` on `(Status)` — used by the converter's `FOR UPDATE SKIP LOCKED` claim.
- `ix_projects_owner_id_created_at` on `(OwnerId, CreatedAt DESC)` — dashboard list query.

**State machine** (`Status` column):

```
                   ┌────────────────────┐
                   │   UploadReceived   │  (created on upload commit)
                   └──────────┬─────────┘
                              │ worker claims
                              ▼
                   ┌────────────────────┐
                   │     Processing     │  (worker running IfcConvert)
                   └──────────┬─────────┘
                  success     │     failure (or 5-min watchdog timeout)
              ┌───────────────┴───────────────┐
              ▼                               ▼
   ┌────────────────────┐          ┌────────────────────┐
   │ ReadyToPublish     │          │       Failed       │
   └──────────┬─────────┘          └────────────────────┘
              │ user clicks Publish
              ▼
   ┌────────────────────┐
   │      Published     │  (terminal for the lifecycle; ShareLink row exists)
   └────────────────────┘
```

`TransitionTo(ProjectStatus next)` is the single method that validates a transition. Anything not on the diagram throws `InvalidStateTransitionException`. There is **no** automatic `Failed → Processing` retry; a user retries by uploading a new file (which becomes a new Project).

---

### `ShareLink` (table `share_links`)

The unguessable, public-token record. Exactly one row per published project (FR-013 idempotency).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `Id` | `uuid` | PK | Internal id (not exposed). |
| `ProjectId` | `uuid` | FK → `projects(Id)` ON DELETE CASCADE, NOT NULL, **unique** | One-to-one. The unique index enforces idempotency. |
| `PublicToken` | `uuid` | NOT NULL, **unique** | The unguessable token used in `/s/{token}`. Separate from `Project.Id` to avoid leaking internal ids (FR-014, FR-025). |
| `QrCodeObjectKey` | `varchar(512)` | NULL | MinIO key for the QR PNG. |
| `CreatedAt` | `timestamptz` | NOT NULL, default `now()` | Set on first publish. |

**Indexes**:
- PK on `Id`.
- **Unique** on `ProjectId` (enforces one-share-per-project, FR-013).
- **Unique** on `PublicToken` (drives the public lookup query).

---

### ASP.NET Identity tables (managed by `AddIdentity`)

These are not designed here — they are the standard `AspNetUsers`, `AspNetRoles`, `AspNetUserRoles`, `AspNetUserClaims`, `AspNetUserLogins`, `AspNetUserTokens`, `AspNetRoleClaims` tables. The MVP uses only `AspNetUsers` and `AspNetRoles`.

`AspNetUsers` is extended with nothing; `OwnerId` on `Project` is a FK to `AspNetUsers.Id`.

---

## Validation rules

These map directly to FR-001…FR-005 and edge cases. Implemented as FluentValidation validators in `Application/Projects/Validators/`.

| Rule | Source | Failure message |
|---|---|---|
| `Name` is 1–200 chars after trim | FR-001 | "Project name is required (1–200 characters)." |
| `Description` is ≤ 2000 chars | FR-001 | "Description must be 2000 characters or less." |
| `ClientLabel` is ≤ 200 chars | FR-001 | "Client label must be 200 characters or less." |
| Uploaded file size ≤ `MAX_IFC_MB` (env, default 100) | FR-004 | "File too large. Maximum allowed size is {N} MB." |
| Uploaded file content starts with `ISO-10303-21;` (first line) | FR-003 | "Not a valid IFC file. The upload must be an .ifc file exported from a supported CAD tool." |
| Uploaded file extension is `.ifc` | FR-033 | "Only .ifc files are supported in this version." |
| `Status` transitions follow the diagram | FR-006 | "Invalid project state transition from {from} to {to}." |
| Publish only allowed when `Status = 'ReadyToPublish'` | FR-011 | "This project is not ready to publish." |

---

## Storage keys (MinIO)

Keys are deterministic per `projectId` and per role. The `Project` row stores the key, never the raw bytes.

| Concern | Bucket | Key |
|---|---|---|
| Original upload | `ifc-files` | `projects/{projectId}/source.ifc` |
| Generated GLB | `glb-files` | `projects/{projectId}/model.glb` |
| Generated thumbnail | `thumbnails` | `projects/{projectId}/thumb.png` |
| Generated QR code | `qrcodes` | `projects/{projectId}/qr.png` |

`{projectId}` is the `Project.Id` (internal Guid). The keys are not user-facing; the public URLs go through presigned GetObject with a 5–15 min TTL.

---

## State surfaces (DTOs)

Three view models consumed by the API responses. Defined in `Application/Projects/Dtos/` and `Application/Sharing/Dtos/`.

### `ProjectDto` (returned by `GET /api/projects/{id}` and `GET /api/projects`)

```json
{
  "id": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Living Room Sofa",
  "description": "...",
  "clientLabel": "Alice",
  "status": "ready-to-publish",
  "thumbnailUrl": "https://minio/...",
  "ifcSizeBytes": 12345678,
  "errorMessage": null,
  "createdAt": "2026-06-09T12:00:00Z",
  "updatedAt": "2026-06-09T12:01:23Z"
}
```

`id` is exposed only on the **authenticated** dashboard endpoints, never on public responses.

### `ProjectSummaryDto` (returned by `GET /api/projects` list)

Same as `ProjectDto` minus `description` (truncated) and `ifcSizeBytes` to keep list payloads light.

### `PublicShareDto` (returned by anonymous `GET /api/share/{token}`)

```json
{
  "name": "Living Room Sofa",
  "clientLabel": "Alice",
  "status": "published",
  "glbUrl": "https://minio/...presigned...",
  "thumbnailUrl": "https://minio/...presigned..."
}
```

**No** `id`, **no** `ownerId`, **no** `errorMessage`, **no** `createdAt` (FR-025). Only what the public viewer needs.

### `PublishResultDto` (returned by `POST /api/projects/{id}/publish`)

```json
{
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "publicToken": "3f2e1d0c-b9a8-7654-3210-fedcba987654",
  "publicUrl": "https://app.example.com/s/3f2e1d0c-b9a8-7654-3210-fedcba987654",
  "qrCodeUrl": "https://minio/...presigned..."
}
```

---

## Migrations

Single initial migration `00000000000000_Initial.cs` created with:
```bash
dotnet ef migrations add Initial \
  --project app/backend/Backend.csproj \
  --startup-project app/backend/Backend.csproj
```

The migration creates:
- `projects` table with all columns above + the 3 indexes.
- `share_links` table with all columns above + the 2 unique indexes.
- The FK `share_links.ProjectId → projects.Id ON DELETE CASCADE`.
- The FK `projects.OwnerId → "AspNetUsers"."Id"`.

ASP.NET Identity schema is created by `AddIdentity` via its own migration (`00000000000001_Identity.cs`).

`Database.Migrate()` is called on startup. The current `EnsureCreated()` is removed.
