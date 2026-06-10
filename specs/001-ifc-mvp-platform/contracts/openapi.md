# OpenAPI / HTTP Contracts: Arch3DAR MVP

**Phase**: 1
**Branch**: `001-ifc-mvp-platform`
**Date**: 2026-06-09
**Spec**: `specs/001-ifc-mvp-platform/spec.md`

> All MVP contracts. Authentication is **cookie-based** (ASP.NET Core Identity); the public share endpoint is the only anonymous one. ProblemDetails (`application/problem+json`) is the canonical error shape (RFC 7807) for non-2xx responses. Every request is expected to carry a `X-Correlation-Id` header (the server generates one if absent and echoes it back).

---

## Conventions

- **Base URL (dev)**: `http://localhost:5000`
- **Base URL (public)**: `${PUBLIC_BASE_URL}` (env)
- **Auth**: `POST /auth/login` sets the `.AspNetCore.Identity.Application` cookie. All `/api/projects/*` endpoints require it. `GET /api/share/{token}` does **not**.
- **Correlation**: every request/response carries `X-Correlation-Id`. Server-side, every `ILogger` event has the same value attached via Serilog `LogContext`.
- **Errors**: `application/problem+json` per RFC 7807. Examples below.
- **Time**: ISO-8601 UTC.
- **JSON casing**: `camelCase`. Enum values are kebab-case strings (e.g. `ready-to-publish`), matching the spec FR-006 status names.

### ProblemDetails shape

```json
{
  "type": "https://arch3dar.com/errors/invalid-state-transition",
  "title": "Invalid state transition",
  "status": 409,
  "detail": "Cannot publish a project in status 'processing'. Wait for conversion to finish.",
  "instance": "/api/projects/8b7e4f1a-.../publish",
  "correlationId": "f0e1d2c3-b4a5-..."
}
```

The `correlationId` field is added to the standard ProblemDetails by the global error middleware; it mirrors the `X-Correlation-Id` header.

---

## Endpoints (summary)

| Method | Path | Auth | Spec FR |
|---|---|---|---|
| POST | `/auth/register` | none | — |
| POST | `/auth/login` | none | — |
| POST | `/auth/logout` | cookie | — |
| GET  | `/api/projects` | cookie | FR-021 |
| POST | `/api/projects` | cookie | FR-001, FR-002 |
| GET  | `/api/projects/{id}` | cookie | FR-022 |
| POST | `/api/projects/{id}/publish` | cookie | FR-011, FR-013 |
| GET  | `/api/share/{token}` | **none** | FR-015, FR-025 |
| GET  | `/health` | none | — |

---

## POST /auth/register

Creates a new user. The first user is the first tenant. After registration, the cookie is set automatically.

**Request**

```http
POST /auth/register
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "correcthorsebatterystaple"
}
```

**Validation**
- `email` must be a valid email.
- `password` must be ≥ 8 chars (Identity default).

**Responses**
- `200 OK` — sets the auth cookie, returns `{ "userId": "..." }`.
- `400 Bad Request` — validation failed (ProblemDetails).
- `409 Conflict` — email already in use.

```json
{ "userId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b" }
```

---

## POST /auth/login

**Request**

```http
POST /auth/login
Content-Type: application/json

{ "email": "alice@example.com", "password": "correcthorsebatterystaple" }
```

**Responses**
- `204 No Content` — cookie set.
- `401 Unauthorized` — bad credentials.

---

## POST /auth/logout

Clears the cookie.

**Responses**
- `204 No Content`

---

## POST /api/projects

Creates a project AND uploads its IFC in a single multipart call (FR-001, FR-002, FR-003, FR-004, FR-005). The project is created in status `upload-received`.

**Request**

```http
POST /api/projects
Cookie: .AspNetCore.Identity.Application=...
Content-Type: multipart/form-data; boundary=----abc

------abc
Content-Disposition: form-data; name="name"

Living Room Sofa
------abc
Content-Disposition: form-data; name="description"

3-seat sofa in walnut
------abc
Content-Disposition: form-data; name="clientLabel"

Alice
------abc
Content-Disposition: form-data; name="file"; filename="project.ifc"
Content-Type: application/octet-stream

<binary>
------abc--
```

**Validation (server-side, in order)**
1. `name` 1–200 chars.
2. `description` ≤ 2000 chars (optional).
3. `clientLabel` ≤ 200 chars (optional).
4. `file` present, size ≤ `MAX_IFC_MB` × 1024 × 1024.
5. `file` content starts with `ISO-10303-21;` (signature check).
6. `file` filename extension is `.ifc`.

The file is streamed directly to MinIO (no in-memory buffering) under key `ifc-files/projects/{projectId}/source.ifc`. The project row is created only after the MinIO upload succeeds (atomicity).

**Responses**

- `201 Created`
  ```json
  {
    "id": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
    "name": "Living Room Sofa",
    "status": "upload-received",
    "createdAt": "2026-06-09T12:00:00Z"
  }
  ```
- `400 Bad Request` — validation failed (ProblemDetails with `type` and `detail`).
- `413 Payload Too Large` — file too big.
- `415 Unsupported Media Type` — not an IFC file.

---

## GET /api/projects

Lists the calling user's projects (FR-021). Tenant-scoped.

**Request**

```http
GET /api/projects
Cookie: .AspNetCore.Identity.Application=...
```

**Query params**
- `status` (optional) — filter by `ProjectStatus` value.
- `limit` (optional, default 50, max 200) — page size.
- `cursor` (optional) — opaque pagination cursor (createdAt + id).

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "items": [
    {
      "id": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
      "name": "Living Room Sofa",
      "clientLabel": "Alice",
      "status": "ready-to-publish",
      "thumbnailUrl": "https://minio:9000/thumbnails/projects/8b.../thumb.png?X-Amz-...",
      "createdAt": "2026-06-09T12:00:00Z"
    }
  ],
  "nextCursor": null
}
```

`thumbnailUrl` is a presigned MinIO URL (TTL 5 min). It is `null` if the thumbnail has not been generated yet (status `upload-received` or `processing`).

---

## GET /api/projects/{id}

Project detail (FR-022).

**Request**

```http
GET /api/projects/8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b
Cookie: .AspNetCore.Identity.Application=...
```

**Responses**
- `200 OK` — `ProjectDto` (see data-model.md).
- `404 Not Found` — caller does not own the project, **or** it doesn't exist (no enumeration leak; SC-006).

---

## POST /api/projects/{id}/publish

Publishes a project. Idempotent (FR-013). On the first call:
1. Validates `Status == 'ready-to-publish'`.
2. Creates a `ShareLink` row (unique on `ProjectId`).
3. Generates a QR code from `${PUBLIC_BASE_URL}/s/{PublicToken}`.
4. Uploads the QR PNG to MinIO.
5. Sets `Project.Status = 'published'`, `PublishedAt = now()`.
6. Returns the result.

On a second call, the existing `ShareLink` is returned without re-uploading.

**Request**

```http
POST /api/projects/8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b/publish
Cookie: .AspNetCore.Identity.Application=...
```

**Responses**

- `200 OK`:
  ```json
  {
    "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
    "publicToken": "3f2e1d0c-b9a8-7654-3210-fedcba987654",
    "publicUrl": "https://app.example.com/s/3f2e1d0c-b9a8-7654-3210-fedcba987654",
    "qrCodeUrl": "https://minio:9000/qrcodes/projects/8b.../qr.png?X-Amz-..."
  }
  ```
- `404 Not Found` — caller does not own the project.
- `409 Conflict` — project status is not `ready-to-publish`. ProblemDetails `type=https://arch3dar.com/errors/invalid-state-transition`.

---

## GET /api/share/{token}  (anonymous, public)

Returns the minimum data needed to render the public page (FR-015, FR-025). No internal ids, no tenant info, no `errorMessage`.

**Request**

```http
GET /api/share/3f2e1d0c-b9a8-7654-3210-fedcba987654
```

**Responses**

- `200 OK`:
  ```json
  {
    "name": "Living Room Sofa",
    "clientLabel": "Alice",
    "status": "published",
    "glbUrl": "https://minio:9000/glb-files/projects/8b.../model.glb?X-Amz-...",
    "thumbnailUrl": "https://minio:9000/thumbnails/projects/8b.../thumb.png?X-Amz-..."
  }
  ```
- `404 Not Found` — token unknown, or the project is not in `published` status yet. Same response either way (no enumeration leak).

---

## GET /health

**Response**
- `200 OK` — `{"status":"ok"}` if the API process is up. Does **not** check Postgres or MinIO. Used by docker-compose `healthcheck`.

---

## Error catalog

| `type` suffix | HTTP | When |
|---|---|---|
| `/errors/validation` | 400 | FluentValidation failure. `errors` object included. |
| `/errors/invalid-ifc` | 415 | File signature check failed. |
| `/errors/file-too-large` | 413 | File > `MAX_IFC_MB`. |
| `/errors/invalid-state-transition` | 409 | `TransitionTo(...)` rejected, or publish called on non-ready project. |
| `/errors/not-found` | 404 | Resource missing OR cross-tenant. |
| `/errors/unauthorized` | 401 | Auth required and missing. |
| `/errors/forbidden` | 403 | Authenticated but not allowed. |
| `/errors/internal` | 500 | Unhandled exception. Stack trace **never** in body (FR-028). |

---

## Python Converter HTTP Contract (internal)

The Python converter sidecar exposes a tiny HTTP API consumed by `HttpModelConverter` in the .NET backend. This is an **internal** contract (not exposed to the browser); it is documented here so the two services can be developed independently.

`POST http://converter:8080/convert`

```json
{ "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b" }
```

Response:

```json
{
  "glbKey": "projects/8b7e4f1a-.../model.glb",
  "thumbnailKey": "projects/8b7e4f1a-.../thumb.png",
  "durationMs": 12345
}
```

Errors:
- `400` if `projectId` not in `Processing` status.
- `500` with `{ "reason": "..." }` on conversion failure (the .NET side persists this as `ErrorMessage`).

The converter itself owns the Postgres polling + `FOR UPDATE SKIP LOCKED` claim; the .NET side never tells it "what" to convert beyond the project id.
