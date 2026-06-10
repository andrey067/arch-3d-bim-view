# OpenAPI / HTTP Contracts: Arch3DAR — Correção MVP

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> API mínima sem autenticação e sem MinIO. Todos os assets servidos diretamente pelo backend (proxied por nginx em produção). **Nenhum endpoint de asset usa redirect.**

---

## Conventions

- **Base URL (dev)**: `http://localhost:5001` (backend direto) ou `https://localhost` (via nginx)
- **Base URL (prod)**: `${PUBLIC_BASE_URL}` — **deve ser HTTPS** para AR
- **Auth**: nenhuma
- **Correlation**: header `X-Correlation-Id` (gerado se ausente)
- **Errors**: `application/problem+json` (RFC 7807)
- **JSON casing**: `camelCase`
- **Asset URLs**: absolutas, same-origin, sem query-string de presign

### ProblemDetails shape

```json
{
  "type": "https://arch3dar.com/errors/conversion-failed",
  "title": "Conversion failed",
  "status": 502,
  "detail": "USDZ generation failed: usd_from_gltf exited 1",
  "correlationId": "f0e1d2c3-b4a5-..."
}
```

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/upload` | none | Upload IFC, converte, retorna link + QR |
| GET | `/share/{token}` | none | Metadados + URLs dos assets |
| GET | `/files/{projectId}/model.glb` | none | Stream GLB |
| GET | `/files/{projectId}/model.usdz` | none | Stream USDZ |
| GET | `/files/{projectId}/thumbnail.png` | none | Stream thumbnail |
| GET | `/share/{token}/qr` | none | QR code SVG |
| GET | `/health` | none | Liveness |

---

## POST /upload

Upload IFC, executa conversão síncrona (backend → converter HTTP), persiste em `/data`, retorna link público.

**Request**

```http
POST /upload
Content-Type: multipart/form-data

file=<binary .ifc>
name=Living Room Sofa   (optional)
```

**Validation**
- `file` obrigatório, extensão `.ifc`
- Primeira linha do conteúdo: `ISO-10303-21`
- Tamanho ≤ `MAX_IFC_MB` (default 100)

**Responses**

- `200 OK`

```json
{
  "token": "a1b2c3d4e5f6789012345678abcdef01",
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Living Room Sofa",
  "status": "Ready",
  "shareUrl": "https://app.example.com/s/a1b2c3d4e5f6789012345678abcdef01",
  "qrSvg": "<svg xmlns=\"http://www.w3.org/2000/svg\" ...></svg>"
}
```

- `400` — campo `file` ausente
- `413` — arquivo grande demais
- `415` — não é IFC válido
- `502` — conversão falhou (GLB ou USDZ)

**Notes**
- Request pode demorar até `CONVERSION_TIMEOUT_S` (default 120s).
- Cliente deve exibir spinner durante upload+conversão.

---

## GET /share/{token}

Retorna dados para o viewer. Token = 32-char hex do `PublicToken`.

**Responses**

- `200 OK` — projeto Ready

```json
{
  "name": "Living Room Sofa",
  "status": "Ready",
  "glbUrl": "https://app.example.com/files/8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b/model.glb",
  "usdzUrl": "https://app.example.com/files/8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b/model.usdz",
  "thumbnailUrl": "https://app.example.com/files/8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b/thumbnail.png"
}
```

- `200 OK` — ainda convertendo

```json
{
  "name": "Living Room Sofa",
  "status": "Converting",
  "glbUrl": null,
  "usdzUrl": null,
  "thumbnailUrl": null
}
```

- `404` — token inválido ou projeto Failed

---

## GET /files/{projectId}/model.glb

Serve o GLB diretamente.

**Responses**
- `200 OK`
  - `Content-Type: model/gltf-binary`
  - `Accept-Ranges: bytes`
  - Body: binary GLB
  - **Sem** header `Location`
- `404` — arquivo ou projeto inexistente

---

## GET /files/{projectId}/model.usdz

Serve o USDZ diretamente para Quick Look / `ios-src`.

**Responses**
- `200 OK`
  - `Content-Type: model/vnd.usdz+zip`
  - Body: binary USDZ (zip)
  - **Sem** header `Location`
- `404` — arquivo ou projeto inexistente

---

## GET /files/{projectId}/thumbnail.png

**Responses**
- `200 OK`, `Content-Type: image/png`
- `404`

---

## GET /share/{token}/qr

Retorna QR code como SVG apontando para `shareUrl`.

**Responses**
- `200 OK`, `Content-Type: image/svg+xml`
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
- `projectId` (uuid string)
- `file` (IFC bytes)

**Response** `200`:

```json
{
  "glbPath": "projects/{id}/model.glb",
  "usdzPath": "projects/{id}/model.usdz",
  "thumbnailPath": "projects/{id}/thumbnail.png",
  "durationMs": 45230
}
```

**Behavior**
- Escreve arquivos em `/data/projects/{id}/` (volume compartilhado).
- Falha `422` se GLB ou USDZ vazios.
- Não usa MinIO.

**Pipeline**
1. `IfcConvert input.ifc output.glb`
2. `IfcConvert input.ifc thumb.png --thumbnail` (fallback: placeholder PNG)
3. `usd_from_gltf output.glb output.usdz`

---

## nginx proxy rules (production)

```nginx
# API
location /upload { proxy_pass http://backend:5000/upload; proxy_redirect off; }
location /share/ { proxy_pass http://backend:5000/share/; proxy_redirect off; }
location /files/ { proxy_pass http://backend:5000/files/; proxy_redirect off; }
location /health { proxy_pass http://backend:5000/health; proxy_redirect off; }

# SPA
location / { try_files $uri $uri/ /index.html; }
```

TLS termination no nginx. Certificado válido obrigatório para testes AR em dispositivos reais.
