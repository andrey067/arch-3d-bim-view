# Arch3DAR

Arch3DAR lets architects and designers share a 3D model (uploaded as `.ifc`) with clients
through a public link. Clients open the link on their phone to view the model in 3D and
place it in their room with augmented reality (Android Scene Viewer + iOS Quick Look).

## Quick Start

```bash
cp app/.env.example app/.env
# Set PUBLIC_BASE_URL and VITE_API_BASE_URL to your HTTPS origin (required for AR)
docker compose -f app/docker-compose.yml up -d --build
docker compose -f app/docker-compose.yml ps
```

Open `https://<your-host>/` to upload an IFC file. You receive a share link and QR code.

## Prerequisites

- Docker 24+ and Docker Compose v2
- TLS certificate for HTTPS (self-signed OK for LAN testing; AR on real phones needs HTTPS)
- 4 GB RAM minimum (8 GB recommended for large IFC files)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   nginx     │────▶│  frontend   │     │  postgres   │
│  :443       │     │   :3000     │     │   :5432     │
└──────┬──────┘     └─────────────┘     └──────▲──────┘
       │                                         │
       ▼                                         │
┌─────────────┐     ┌─────────────┐              │
│   backend   │────▶│  converter  │              │
│   :5000     │     │   :8080     │              │
└──────┬──────┘     └──────┬──────┘              │
       │                   │                     │
       └─────── /data (project_data volume) ─────┘
```

- **frontend** — React + Vite + `<model-viewer>` (upload + public share page)
- **backend** — ASP.NET Core 9 API; serves files directly from `/data`
- **converter** — Python sidecar: IfcConvert → GLB, `usd_from_gltf` → USDZ
- **postgres** — project metadata (token, status, paths)
- **nginx** — TLS termination, reverse proxy (no redirects on `/files/`)

## Local storage layout

```
/data/projects/{projectId}/
  original.ifc
  model.glb
  model.usdz
  thumbnail.png
```

Public URLs (same origin, no presigned redirects):

- `GET /files/{projectId}/model.glb` — `Content-Type: model/gltf-binary`
- `GET /files/{projectId}/model.usdz` — `Content-Type: model/vnd.usdz+zip`
- `GET /files/{projectId}/thumbnail.png` — `Content-Type: image/png`

## Services

| Service   | Description                         | Port        |
|-----------|-------------------------------------|-------------|
| nginx     | HTTPS reverse proxy                 | 80, 443     |
| frontend  | React upload + share viewer         | 3000        |
| backend   | ASP.NET Core 9 API                  | 5000 (5001) |
| converter | IFC → GLB → USDZ                    | 8080        |
| postgres  | PostgreSQL 16                       | 5432        |

## API (MVP)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload IFC, convert, return share link + QR |
| GET | `/share/{token}` | Viewer metadata + asset URLs |
| GET | `/files/{id}/model.glb` | Stream GLB |
| GET | `/files/{id}/model.usdz` | Stream USDZ (iOS Quick Look) |
| GET | `/share/{token}/qr` | QR code SVG |
| GET | `/health` | Liveness |

## Development

```bash
make build-backend
make test-backend
make test-frontend
make verify-no-minio
```

See `specs/001-ifc-mvp-platform/quickstart.md` for end-to-end validation.
