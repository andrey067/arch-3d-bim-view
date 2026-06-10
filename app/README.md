# Arch3DAR

Arch3DAR is a SaaS that lets architects, interior designers, and custom-furniture
manufacturers share a single 3D model (uploaded as an `.ifc` file) with their
client through a public link that the client can open on their phone to view
the model in 3D and place it in their real environment with augmented reality.

The product is positioned as a 3D sharing platform for architecture, interiors,
and custom furniture. It is not a BIM platform, not a coordination tool, and
not an engineering suite.

## Quick Start

```bash
git clone <repository-url>
cd arch3dar
cp app/.env.example app/.env
docker compose -f app/docker-compose.yml up -d
docker compose -f app/docker-compose.yml ps
```

The backend will apply EF migrations on startup. Open `http://localhost:3000`
to use the dashboard.

## Prerequisites

- Docker 24+ and Docker Compose v2
- 4 GB RAM minimum (8 GB recommended for large IFC files)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  frontend   │     │   backend   │────▶│  postgres   │
│  :3000      │────▶│   :5000     │     │   :5432     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  converter  │────▶│    minio    │
                    │   :8080     │     │   :9000     │
                    └─────────────┘     └─────────────┘
```

- **frontend** — React 18 + Vite + `<model-viewer>`. No BIM components.
- **backend** — ASP.NET Core 9 API with MediatR, Serilog, EF Core, Identity.
- **converter** — Python sidecar running IfcOpenShell `IfcConvert`; claims
  projects via Postgres `FOR UPDATE SKIP LOCKED`.
- **postgres** — relational state for projects, share links, and Identity.
- **minio** — S3-compatible object storage with four buckets: `ifc-files`,
  `glb-files`, `thumbnails`, `qrcodes`.

## Services

| Service    | Description                                          | Port          |
|------------|------------------------------------------------------|---------------|
| frontend   | React + Vite 3D viewer (no BIM features)             | 3000          |
| backend    | ASP.NET Core 9 API                                   | 5000 (→ 5001) |
| postgres   | PostgreSQL 16                                        | 5432          |
| minio      | S3-compatible object storage                         | 9000, 9001    |
| converter  | IFC-to-GLB conversion (IfcOpenShell `IfcConvert`)    | 8080          |

## Environment Variables

Copy `app/.env.example` to `app/.env` and adjust as needed. The defaults
are safe for local development. Never commit `.env` to source control.

Key variables:

- `POSTGRES_*` — Postgres credentials.
- `MINIO_*` — MinIO root credentials, bucket names, presigned-URL TTL.
- `PUBLIC_BASE_URL` — the public origin used to build share links and QR
  codes. The share URL is `${PUBLIC_BASE_URL}/s/{publicToken}`.
- `MAX_IFC_MB` — maximum upload size in MB. Default `100`.
- `CONVERSION_TIMEOUT_S` — per-conversion timeout in seconds. Default `300`.
- `CONVERTER_URL` — the converter sidecar URL. Default
  `http://converter:8080`.
- `CORS_ALLOWED_ORIGINS` — semicolon-separated list of allowed origins.
  Default `http://localhost:3000`.

## Usage

### Create an account

Open `http://localhost:3000`, click "Create one" on the sign-in page, and
provide an email + password (≥ 8 chars). After registering, the dashboard
is reachable.

### Upload an IFC file

1. Sign in and click "New project".
2. Drag and drop your `.ifc` file (or click the dropzone to choose).
3. Optionally add a description and a client label.
4. Click "Upload". The project is created and conversion starts automatically.

### Share with your client

Once the project status reads **Ready to publish**, click "Publish" to
generate a public link and a QR code. The status moves to **Published**.

### Client opens the link

The client opens the link in a modern mobile or desktop browser. The page
shows the model name, a thumbnail, and the interactive 3D model with
orbit / zoom / pan / fullscreen. On Android Chrome (and iOS Safari where
supported), a "View in your space" button launches the device's native
AR experience and places the model at real-world scale.

## Development

### Frontend

```bash
cd app/frontend
npm install
npm run dev        # http://localhost:5173
npm run lint
npm test
npm run test:e2e   # Playwright (requires full stack via docker compose)
```

### Backend

```bash
cd app/backend
dotnet restore
dotnet build
dotnet test
dotnet run         # http://localhost:5000
```

### Converter

```bash
cd app/converter
pip install -r requirements.txt
IFCCONVERT_PATH=$(which IfcConvert) uvicorn converter_service:app --reload
```

### Makefile shortcuts

```bash
make up            # docker compose up -d
make down          # docker compose down
make logs          # docker compose logs -f
make test-backend
make test-frontend
make e2e
make audit-bim     # fails if any "BIM" wording is found in user-facing surfaces
```

## API

See `specs/001-ifc-mvp-platform/contracts/openapi.md` for the full HTTP
contract. The high-level surface:

- `POST /auth/register` / `POST /auth/login` / `POST /auth/logout`
- `GET /api/me`
- `POST /api/projects` (multipart: name, description?, clientLabel?, file)
- `GET /api/projects`
- `GET /api/projects/{id}`
- `POST /api/projects/{id}/publish`
- `GET /api/share/{token}` (anonymous, public page)
- `GET /api/share/{token}/qr` (PNG)
- `GET /health`

## MinIO Buckets

| Bucket      | Contents                | Lifecycle                |
|-------------|-------------------------|--------------------------|
| ifc-files   | Original IFC uploads    | Long retention           |
| glb-files   | Generated 3D models     | Long retention           |
| thumbnails  | Generated preview PNGs  | Long retention           |
| qrcodes     | Generated QR code PNGs  | Long retention           |

Public delivery is via presigned GetObject URLs (TTL 10 minutes by default).
The backend never proxies binary content.

## Troubleshooting

### The converter container is unhealthy

```bash
docker compose logs converter
docker compose exec converter IfcConvert --version
```

The container's `IfcConvert` binary is pinned to a specific version and
SHA256. If the download is broken, update the URLs in
`app/converter/Dockerfile`.

### Uploads return 413

`MAX_IFC_MB` in `.env` is the ceiling. Increase it (and the Kestrel /
nginx body-size limit) if your use case requires it.

### Cross-tenant reads return 404

This is intentional. The product hides cross-tenant data existence to
prevent enumeration (see FR-024 / SC-006 in the spec).

## License

Proprietary — Internal use only.
