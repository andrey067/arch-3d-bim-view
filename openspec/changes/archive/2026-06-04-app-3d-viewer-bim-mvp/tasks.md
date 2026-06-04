## 1. Infrastructure & Project Scaffolding

- [x] 1.1 Create project root directory structure (`/app/frontend`, `/app/backend`, `/app/converter`)
- [x] 1.2 Create `docker-compose.yml` with all 6 services (postgres, minio, backend, frontend, converter, nginx)
- [x] 1.3 Create `.env` file with sensible defaults (DB credentials, MinIO keys, bucket names)
- [x] 1.4 Create `nginx.conf` with reverse proxy rules, SPA fallback, `client_max_body_size 500m`, and SSL termination placeholders
- [x] 1.5 Create named volume configuration for postgres and minio data persistence
- [x] 1.6 Add health checks to all services in docker-compose

## 2. Backend — ASP.NET Core API Setup

- [x] 2.1 Scaffold ASP.NET Core 9 Web API project with Minimal APIs in `/app/backend`
- [x] 2.2 Add NuGet packages: `Microsoft.EntityFrameworkCore`, `Npgsql.EntityFrameworkCore.PostgreSQL`, `Minio`, `AWSSDK.S3` (for MinIO compatibility)
- [x] 2.3 Create `Project` entity model with fields: `Id` (Guid), `Name`, `Description`, `IfcObjectKey`, `GlbObjectKey`, `ThumbnailObjectKey`, `Status` (enum), `CreatedAt`
- [x] 2.4 Configure EF Core `DbContext` with PostgreSQL connection string from environment variables
- [x] 2.5 Create initial EF Core migration and configure auto-migration on startup
- [x] 2.6 Configure `Program.cs` with CORS (allow frontend origin), MinIO client registration, and EF Core DI

## 3. Backend — MinIO Integration

- [x] 3.1 Implement `MinioService` class with methods: `EnsureBucketsExistAsync`, `UploadFileAsync`, `GetPresignedUrlAsync`
- [x] 3.2 Register `MinioService` as a singleton in DI
- [x] 3.3 Add startup bucket creation logic calling `EnsureBucketsExistAsync` for `ifc-files`, `glb-files`, `thumbnails`

## 4. Backend — Upload Endpoint

- [x] 4.1 Implement `POST /api/projects/upload` accepting multipart form with `file` (`.ifc`) and `name` (string)
- [x] 4.2 Add file validation: check `.ifc` extension, validate IFC header (ISO-10303-21 magic bytes), enforce 500 MB max size
- [x] 4.3 Stream uploaded file to MinIO `ifc-files` bucket with key `projects/{projectId}/{filename}.ifc`
- [x] 4.4 Create `Project` record in PostgreSQL with status `Uploaded` and return `201 Created` with project details

## 5. Backend — Project Management API

- [x] 5.1 Implement `GET /api/projects` returning paginated list of projects with id, name, description, status, thumbnailUrl, createdAt
- [x] 5.2 Implement `GET /api/projects/{id}` returning full project details including presigned URLs for IFC, GLB, and thumbnail
- [x] 5.3 Generate presigned URLs with 1-hour expiry in project detail responses
- [x] 5.4 Add `404 Not Found` handling for non-existent project IDs

## 6. Backend — Share Endpoints

- [x] 6.1 Implement `GET /share/{id}` returning the React SPA index.html (delegates to frontend routing)
- [x] 6.2 Implement `GET /api/share/{id}` returning project data (GLB presigned URL, metadata) for the viewer to consume
- [x] 6.3 Add Open Graph meta tag support: og:title, og:description, og:image (thumbnail) in share page response

## 7. Converter — IFC-to-GLB Service

- [x] 7.1 Create `/app/converter/Dockerfile` based on Ubuntu with IfcOpenShell installed (via apt or pre-built binary)
- [x] 7.2 Create converter worker script (Python or shell) that polls MinIO for new IFC files, runs `IfcConvert`, and uploads GLB to `glb-files` bucket
- [x] 7.3 Update project status to `Processing` when conversion starts, `Completed` on success, `Failed` on error
- [x] 7.4 Store GLB in MinIO at `projects/{projectId}/model.glb` and update `GlbObjectKey` in database
- [x] 7.5 Add error handling: log conversion errors, handle timeouts for large files, retry logic (max 1 retry)

## 8. Thumbnail Generation

- [x] 8.1 Implement thumbnail generation in the converter pipeline (use IfcConvert snapshot or headless Three.js render)
- [x] 8.2 Store generated PNG thumbnail in MinIO `thumbnails` bucket at `projects/{projectId}/thumbnail.png`
- [x] 8.3 Update `ThumbnailObjectKey` in database after successful thumbnail generation
- [x] 8.4 Handle thumbnail generation failure gracefully (non-blocking, fallback to placeholder)

## 9. Frontend — Project Setup

- [x] 9.1 Scaffold React + TypeScript + Vite project in `/app/frontend`
- [x] 9.2 Install dependencies: `react-router-dom`, `@thatopen/components`, `web-ifc`, `@thatopen/ui-components`, `@google/model-viewer`, `three`, `axios`
- [x] 9.3 Configure Vite proxy for `/api` and `/share` to backend during development
- [x] 9.4 Set up React Router with lazy-loaded routes: `/` (Projects), `/upload`, `/view/:id`, `/share/:id`, `/share/:id/ar`
- [x] 9.5 Create shared API client module with Axios instance and base URL configuration

## 10. Frontend — Upload Page

- [x] 10.1 Create `UploadPage` component with drag-and-drop file input (`.ifc` only) and project name text field
- [x] 10.2 Implement file size validation (500 MB max) with user-friendly error message
- [x] 10.3 Implement upload with progress indicator (axios `onUploadProgress`)
- [x] 10.4 On successful upload, redirect to the project viewer page
- [x] 10.5 Display upload errors (invalid file type, corrupted IFC, server error) with clear messages

## 11. Frontend — Projects Page

- [x] 11.1 Create `ProjectsPage` component fetching project list from `GET /api/projects`
- [x] 11.2 Render project cards with thumbnail, name, status badge, and creation date
- [x] 11.3 Add "View" button on each card linking to `/view/{id}` and copy-to-clipboard for share URL
- [x] 11.4 Add "Upload New" button linking to `/upload`
- [x] 11.5 Handle loading state (skeleton cards) and empty state ("No projects yet")

## 12. Frontend — BIM Viewer Page

- [x] 12.1 Create `ViewerPage` component that fetches project data and GLB presigned URL from `GET /api/projects/{id}`
- [x] 12.2 Initialize That Open Components: `Components`, `World`, `IfcLoader`, `Camera`, `Renderer`
- [x] 12.3 Load GLB model into the scene and auto-frame camera to fit entire model
- [x] 12.4 Implement camera controls: orbit (left mouse), pan (right/middle mouse), zoom (scroll wheel)
- [x] 12.5 Implement element selection on click with visual highlight (outline/color change)
- [x] 12.6 Create properties panel showing selected element's GlobalId, IFC type, name, description, quantities
- [x] 12.7 Create spatial tree panel showing hierarchical structure (Site → Building → Storey → Elements) with IFC classification
- [x] 12.8 Implement click-to-select in spatial tree (fly camera to element, highlight in 3D)
- [x] 12.9 Add "View in AR" button linking to `/share/{id}/ar`
- [x] 12.10 Handle loading state (spinner while model loads) and error state (model load failure, expired URL)

## 13. Frontend — AR Viewer Page

- [x] 13.1 Create `ARViewerPage` component using `<model-viewer>` with the GLB presigned URL
- [x] 13.2 Configure `<model-viewer>` attributes: `ar`, `ar-modes="webxr scene-viewer quick-look"`, `camera-controls`, `autoplay`
- [x] 13.3 Add "View in AR" button that triggers the AR experience
- [x] 13.4 Handle HTTPS requirement: show warning if page is loaded over HTTP
- [x] 13.5 Add "Back to Viewer" link returning to BIM viewer
- [x] 13.6 Handle loading and error states for GLB model in AR viewer

## 14. Frontend — Share Page (Public)

- [x] 14.1 Create `SharePage` component that fetches project data from `GET /api/share/{id}` (no auth)
- [x] 14.2 Embed the BIM viewer (reuse ViewerPage components) with the project's GLB model
- [x] 14.3 Set Open Graph meta tags dynamically (title, description, thumbnail image)
- [x] 14.4 Add "View in AR" button linking to `/share/{id}/ar`
- [x] 14.5 Handle "Project not found" state with a friendly 404 page

## 15. Integration & End-to-End Flow

- [ ] 15.1 Test full upload flow: upload IFC → backend stores → converter processes → GLB available → viewer loads
- [ ] 15.2 Test share flow: open `/share/{id}` → BIM viewer renders → AR viewer works on mobile
- [ ] 15.3 Test error scenarios: invalid IFC, oversized file, conversion failure, expired presigned URL
- [ ] 15.4 Verify Docker Compose `docker compose up -d` works on a clean VPS
- [x] 15.5 Create README.md with setup instructions (prerequisites, `docker compose up`, environment variables)