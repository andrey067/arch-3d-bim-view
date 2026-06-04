## Why

Architects need a frictionless way to share BIM models with clients who lack specialized software. Clients must be able to open a link, explore the 3D model in any browser, inspect element properties, and optionally view the model in augmented reality on their phone — no installs, no accounts, no complexity.

## What Changes

- New **IFC upload endpoint** accepting `.ifc` files up to 500 MB
- New **MinIO storage** integration with dedicated buckets for IFC originals, GLB derivatives, and thumbnails
- New **IFC-to-GLB conversion pipeline** using IfcConvert in a sidecar container
- New **project management API** for listing, viewing details, and managing uploaded models
- New **BIM viewer frontend** using That Open Components for 3D navigation, element selection, and property inspection
- New **AR viewer** using `<model-viewer>` supporting WebXR, Scene Viewer (Android), and Quick Look (iOS)
- New **shareable public URLs** per project (no authentication required for viewing)
- New **thumbnail generation service** producing PNG previews from IFC models
- New **Docker Compose deployment** with PostgreSQL, MinIO, backend, frontend, converter, and nginx

## Capabilities

### New Capabilities

- `ifc-upload-and-storage`: Upload IFC files via multipart form, persist originals in MinIO `ifc-files` bucket, validate file type and size
- `ifc-conversion`: Asynchronous IFC-to-GLB conversion using IfcConvert in a dedicated converter service, store results in MinIO `glb-files` bucket
- `project-management`: REST API to create projects on upload, list all projects with metadata, retrieve project details including storage keys
- `bim-viewer`: Browser-based 3D BIM viewer with orbit/pan/zoom, spatial tree navigation, element selection and highlighting, IFC property inspection, and IFC classification display
- `ar-viewer`: Augmented reality viewer using `<model-viewer>` with WebXR, Scene Viewer, and Quick Look fallback, accessible from the shared project page
- `project-sharing`: Generate and serve public share links (`/share/{id}`) rendering the BIM and AR viewer pages with no authentication required
- `thumbnail-generation`: Render IFC model to a PNG thumbnail image during conversion, store in MinIO `thumbnails` bucket
- `infrastructure`: Docker Compose orchestration of all services (postgres, minio, backend, frontend, converter, nginx) ready for VPS deployment and future Kubernetes migration

### Modified Capabilities

_None — this is a greenfield project._

## Impact

- **New codebase** at `/app` with `frontend/`, `backend/`, `converter/`, and `docker-compose.yml`
- **Frontend**: React + TypeScript + Vite SPA using `@thatopen/components`, `web-ifc`, `@thatopen/ui-components`, `@google/model-viewer`, and Three.js
- **Backend**: ASP.NET Core 9 Web API with PostgreSQL (Entity Framework Core) and MinIO SDK
- **Converter**: Linux container running IfcOpenShell `IfcConvert`
- **Infrastructure**: Docker Compose with 6 services; nginx reverse proxy in front
- **Storage**: MinIO with 3 buckets — `ifc-files`, `glb-files`, `thumbnails`
- **Database**: PostgreSQL with `Projects` table tracking storage keys and conversion status
