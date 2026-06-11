# OpenAPI / HTTP Contracts: Arch3DAR — IFC/SketchUp MVP

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> API mínima sem autenticação. Upload `.ifc`, `.dae`, ou `.obj`. **`.skp` rejeitado.** Assets servidos diretamente (sem redirect).

---

## Conventions

- **Base URL (dev)**: `http://localhost:5001` ou `https://localhost` (nginx)
- **Base URL (prod)**: `${PUBLIC_BASE_URL}` — **HTTPS** para AR
- **Auth**: nenhuma
- **Correlation**: header `X-Correlation-Id`
- **Errors**: `application/problem+json` (RFC 7807)
- **JSON casing**: `camelCase`

### ProblemDetails shape

```json
{
  "type": "https://arch3dar.com/errors/conversion-failed",
  "title": "Conversion failed",
  "status": 502,
  "detail": "DAE import failed: Blender exited 1",
  "correlationId": "f0e1d2c3-b4a5-..."
}
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Upload IFC/DAE/OBJ, convert, return link + QR |
| GET | `/share/{token}` | Metadata + asset URLs |
| GET | `/files/{projectId}/model.glb` | Stream GLB |
| GET | `/files/{projectId}/model.usdz` | Stream USDZ |
| GET | `/files/{projectId}/thumbnail.webp` | Stream thumbnail |
| GET | `/share/{token}/qr` | QR code SVG |
| GET | `/health` | Liveness |

---

## POST /upload

**Request**

```http
POST /upload
Content-Type: multipart/form-data

file=<binary .ifc | .dae | .obj>
name=Kitchen Island   (optional)
```

**Validation**

| Format | Extension | Signature |
|---|---|---|
| IFC | `.ifc` | First line `ISO-10303-21` |
| DAE | `.dae` | XML with `<COLLADA` root or COLLADA namespace |
| OBJ | `.obj` | Text Wavefront with `v ` / `f ` lines |
| SKP | `.skp` | **Rejected 415** — not supported; return SketchUp export instructions |

- Tamanho ≤ `MAX_UPLOAD_MB` (default 100)

**Responses**

- `200 OK`

```json
{
  "token": "a1b2c3d4e5f6789012345678abcdef01",
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Kitchen Island",
  "sourceFormat": "dae",
  "status": "Ready",
  "shareUrl": "https://app.example.com/s/a1b2c3d4e5f6789012345678abcdef01",
  "qrSvg": "<svg xmlns=\"http://www.w3.org/2000/svg\" ...></svg>"
}
```

- `400` — `file` missing
- `413` — file too large
- `415` — invalid format / signature (including `.skp` with Collada export hint)
- `502` — conversion failed (GLB, USDZ, or thumbnail)

**Notes**
- Timeout: up to `IFC_CONVERSION_TIMEOUT_S` (120s) or `MESH_CONVERSION_TIMEOUT_S` (180s).
- Client file picker `accept`: `.ifc,.dae,.obj` only.
- Client shows spinner during upload+conversion.

---

## GET /share/{token}

**200 OK — Ready**

```json
{
  "name": "Kitchen Island",
  "status": "Ready",
  "sourceFormat": "dae",
  "glbUrl": "https://app.example.com/files/8b7e4f1a-.../model.glb",
  "usdzUrl": "https://app.example.com/files/8b7e4f1a-.../model.usdz",
  "thumbnailUrl": "https://app.example.com/files/8b7e4f1a-.../thumbnail.webp"
}
```

**200 OK — Converting**

```json
{
  "name": "Kitchen Island",
  "status": "Converting",
  "sourceFormat": "dae",
  "glbUrl": null,
  "usdzUrl": null,
  "thumbnailUrl": null
}
```

- `404` — invalid token or Failed project

---

## GET /files/{projectId}/model.glb

- `200 OK` — `Content-Type: model/gltf-binary`, `Accept-Ranges: bytes`, no `Location`
- `404`

---

## GET /files/{projectId}/model.usdz

- `200 OK` — `Content-Type: model/vnd.usdz+zip`, no `Location`
- `404`

---

## GET /files/{projectId}/thumbnail.webp

- `200 OK` — `Content-Type: image/webp`
- `404`

---

## GET /share/{token}/qr

- `200 OK` — `Content-Type: image/svg+xml`
- `404`

---

## GET /health

```json
{ "status": "ok" }
```

---

## Converter sidecar contract (internal)

`POST http://converter:8080/convert`

**Request**: `multipart/form-data`
- `projectId` (uuid)
- `sourceFormat` (`ifc` | `dae` | `obj`)
- `file` (original bytes)

**Response** `200`:

```json
{
  "glbPath": "projects/{id}/model.glb",
  "usdzPath": "projects/{id}/model.usdz",
  "thumbnailPath": "projects/{id}/thumbnail.webp",
  "durationMs": 87230
}
```

**Pipeline by format**

IFC:
1. Write `original.ifc`
2. `IfcConvert` → `model.glb`
3. `glb_normalize`
4. `usd_from_gltf` → `model.usdz`
5. `render_thumbnail.py` → `thumbnail.webp`

DAE / OBJ:
1. Write `original.dae` or `original.obj`
2. `blender -b --python mesh_to_glb.py -- --format dae|obj` → `model.glb`
3. `glb_normalize`
4. `usd_from_gltf` → `model.usdz`
5. `render_thumbnail.py` → `thumbnail.webp`

**Errors**
- `422` — empty GLB/USDZ/WebP
- `504` — timeout

---

## nginx proxy rules

```nginx
location /upload  { proxy_pass http://backend:5000/upload;  proxy_redirect off; }
location /share/  { proxy_pass http://backend:5000/share/;  proxy_redirect off; }
location /files/  { proxy_pass http://backend:5000/files/;  proxy_redirect off; }
location /health  { proxy_pass http://backend:5000/health;  proxy_redirect off; }
location /        { try_files $uri $uri/ /index.html; }
```

TLS termination at nginx. Valid certificate required for device AR testing.
