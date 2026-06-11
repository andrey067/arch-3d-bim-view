# Arch3DAR

Arch3DAR lets architects and designers share a 3D model (uploaded as `.ifc` or `.skp`) with clients
through a public link. Clients open the link on their phone to view the model in 3D and
place it in their room with augmented reality (Android Scene Viewer + iOS Quick Look).

## Quick Start

```bash
cp app/.env.example app/.env
# Set PUBLIC_BASE_URL and VITE_API_BASE_URL to your HTTPS origin (required for AR)
docker compose -f app/docker-compose.yml up -d --build
docker compose -f app/docker-compose.yml ps
```

Open `https://<your-host>/` to upload an IFC or SKP file. You receive a share link and QR code.

## Prerequisites

- Docker 24+ and Docker Compose v2
- TLS certificate for HTTPS (mkcert recommended — see [iPhone AR setup](#iphone-quick-look-setup) below)
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
- **converter** — Python sidecar: IFC → GLB → tabletop normalize → USDZ (see [Conversion pipeline](#conversion-pipeline))
- **postgres** — project metadata (token, status, paths)
- **nginx** — TLS termination, reverse proxy (no redirects on `/files/`)

## Local storage layout

```
/data/projects/{projectId}/
  original.ifc   (or original.skp)
  model.glb
  model.usdz
  thumbnail.webp
```

Public URLs (same origin, no presigned redirects):

- `GET /files/{projectId}/model.glb` — `Content-Type: model/gltf-binary`
- `GET /files/{projectId}/model.usdz` — `Content-Type: model/vnd.usdz+zip`
- `GET /files/{projectId}/thumbnail.webp` — `Content-Type: image/webp`

## Services

| Service   | Description                         | Port        |
|-----------|-------------------------------------|-------------|
| nginx     | HTTPS reverse proxy                 | 80, 443     |
| frontend  | React upload + share viewer         | 3000        |
| backend   | ASP.NET Core 9 API                  | 5000 (5001) |
| converter | IFC/SKP → GLB → USDZ + WebP thumbnail | 8080        |
| postgres  | PostgreSQL 16                       | 5432        |

## API (MVP)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload IFC or SKP, convert, return share link + QR |
| GET | `/share/{token}` | Viewer metadata + asset URLs |
| GET | `/files/{id}/model.glb` | Stream GLB |
| GET | `/files/{id}/model.usdz` | Stream USDZ (iOS Quick Look) |
| GET | `/share/{token}/qr` | QR code SVG |
| GET | `/health` | Liveness |

## Conversion pipeline

When a user uploads an `.ifc` or `.skp` file, the backend saves it under `/data/projects/{projectId}/`
and calls the converter sidecar (`POST /convert`). The converter runs a **synchronous**
pipeline; if any step fails, the project is marked `failed` and the upload returns `502`.

**IFC path**

```
IFC bytes → IfcConvert → model.glb → glb_normalize → usd_from_gltf → model.usdz
                                              ↘ render_thumbnail → thumbnail.webp
```

**SKP path**

```
SKP bytes → Blender headless (SKP→GLB) → model.glb → glb_normalize → usd_from_gltf → model.usdz
                                                              ↘ render_thumbnail → thumbnail.webp
```

```
IFC bytes
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. IfcConvert (-y)                                           │
│    original.ifc  →  model.glb                                │
│    One GLB scene with multiple meshes (walls, slabs, etc.).   │
│    Each mesh node carries a 4×4 matrix placing it in world   │
│    coordinates (IfcOpenShell does not merge geometry).         │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. glb_normalize.py  (AR_MAX_EXTENT_M, default 0.5 m)        │
│    a) Bake node matrices into vertex positions               │
│       → keeps IFC parts assembled (fixes “broken” AR model)  │
│    b) Uniform scale so longest axis = AR_MAX_EXTENT_M          │
│       → tabletop miniature, not real-world building size     │
│    c) Lift so min(Y) = 0                                     │
│       → model rests on detected floor/table surface in AR    │
│    Overwrites model.glb in place.                            │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. usd_from_gltf (Google)                                    │
│    model.glb  →  model.usdz                                  │
│    Produces Quick Look–compatible USDZ (model.usdc inside zip).│
│    Failure or empty output → entire conversion fails (422).    │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Thumbnail (Blender EEVEE render)                           │
│    render_thumbnail.py  →  thumbnail.webp (512px, fallback grey) │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Backend marks project Ready, returns share URL + QR         │
└──────────────────────────────────────────────────────────────┘
```

### Why baking node matrices matters

IfcConvert exports each IFC product as a separate glTF node with its own `matrix`
translation (often tens of metres apart). Scaling only local vertex coordinates
without applying those matrices causes parts to **fly apart** in AR. `glb_normalize.py`
multiplies each mesh vertex by its node matrix, then removes the matrix — the
assembly stays intact.

### Tabletop AR scale (`AR_MAX_EXTENT_M`)

| Value | Effect |
|-------|--------|
| `0.5` (default) | Longest side ≈ 50 cm — fits on a coffee table |
| `0.8` | Slightly larger desk preview |
| `2.0` | Room-scale (needs physical space) |

Set in `app/.env` or `docker-compose.yml` under the `converter` service. **Re-upload
the IFC** after changing — existing files on disk are not reprocessed automatically.

### iOS vs Android delivery

| Platform | Asset | How it is loaded |
|----------|-------|------------------|
| Web viewer | `model.glb` | `<model-viewer src=…>` |
| iPhone Quick Look | `model.usdz` | `<model-viewer ios-src=…>` + `<a rel="ar">` fallback |
| Android Scene Viewer | `model.glb` | `<model-viewer ar-modes="… scene-viewer …">` |

Both GLB and USDZ are served from the same HTTPS origin (`/files/{projectId}/…`)
with correct MIME types and **no redirects** (required for Quick Look).

### Converter environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_ROOT` | `/data` | Shared volume with backend |
| `IFCCONVERT_PATH` | `/usr/local/bin/IfcConvert` | IfcOpenShell CLI |
| `BLENDER_PATH` | `/opt/blender/blender` | Headless Blender (SKP import + thumbnail) |
| `USD_FROM_GLTF_PATH` | `/usr/local/bin/usd_from_gltf` | GLB → USDZ |
| `IFC_CONVERSION_TIMEOUT_S` | `120` | IFC subprocess timeout |
| `SKP_CONVERSION_TIMEOUT_S` | `180` | SKP/Blender subprocess timeout |
| `AR_MAX_EXTENT_M` | `0.5` | Tabletop longest-axis size (metres) |

### Manual re-conversion (existing project)

```bash
PROJECT_ID=<uuid>
docker exec arch3dar-converter bash -c "
  DIR=/data/projects/$PROJECT_ID
  IfcConvert -y \$DIR/original.ifc \$DIR/model.glb
  python3 -c \"from glb_normalize import normalize_glb_for_ar; normalize_glb_for_ar('\\\$DIR/model.glb', 0.5)\"
  usd_from_gltf \$DIR/model.glb \$DIR/model.usdz
"
```

## Development

```bash
make build-backend
make test-backend
make test-frontend
make verify-no-minio
```

See `specs/001-ifc-mvp-platform/quickstart.md` for end-to-end validation.

## iPhone Quick Look setup

Quick Look on iOS downloads the USDZ in a separate process. A **CA that the
iPhone trusts** is required — self-signed certificates cause Quick Look to
open an empty AR scene. Use [mkcert](https://github.com/FiloSottile/mkcert) to
generate a local CA + leaf cert that the iPhone will trust after one install.

### 1. Generate certs on the host

```bash
brew install mkcert nss        # one-time
mkcert -install               # creates local CA in macOS keychain
cd app/nginx/certs
mkcert -cert-file fullchain.pem -key-file privkey.pem 192.168.68.51 localhost 127.0.0.1
```

Rebuild the nginx image so the new cert is baked in:

```bash
cd app && docker compose build nginx && docker compose up -d nginx
```

### 2. Install the mkcert CA on the iPhone

1. In Finder, locate `$(mkcert -CAROOT)/rootCA.pem` (default
   `~/Library/Application Support/mkcert/rootCA.pem`).
2. AirDrop it to the iPhone, or serve it from a local web server and open the
   link in Safari.
3. iOS prompts to install the profile. Confirm in **Settings → General → VPN & Device Management**.
4. Enable full trust: **Settings → General → About → Certificate Trust Settings**
   → enable **Enable Full Trust for Root Certificates** for the mkcert root.

### 3. Validate AR on iPhone

Use **Safari** (Edge/Chrome on iOS use WKWebView and may handle AR differently).
Open the share link, confirm the GLB loads in the web viewer, then tap **AR**
or the **View in AR** card. Quick Look should open with the IFC model and
**Object / AR** tabs both populated.
