# Quickstart Validation: Arch3DAR — IFC/SKP → Web 3D + AR

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> Cenários executáveis: upload IFC **ou** SKP → GLB + USDZ + thumbnail WebP → AR Android + iPhone, sem MinIO.

---

## Prerequisites

| Tool | Min version | Why |
|---|---|---|
| Docker + Docker Compose | 24+ | Full stack incl. Blender |
| `curl`, `jq` | any | API smoke tests |
| HTTPS + valid cert | TLS | Quick Look requires HTTPS |
| iPhone Safari + Android Chrome | iOS 15+ / Android 10+ | Manual AR |
| Sample `.ifc` | ~200 KB | `app/tests/backend/Integration/Fixtures/sample.ifc` |
| Sample `.skp` | ~1–5 MB | Export from SketchUp or test fixture (Phase B) |

**Verify no MinIO**:

```bash
docker compose -f app/docker-compose.yml config --services | grep -i minio
# empty output expected
```

---

## 0. Boot the stack

```bash
cd app
cp .env.example .env
# PUBLIC_BASE_URL=https://<your-host>
docker compose up -d --build
curl -s http://localhost:5001/health
# {"status":"ok"}
curl -s http://localhost:8080/health   # converter
# {"status":"ok"}
```

Expected services: `postgres`, `converter`, `backend`, `frontend`, `nginx` — **no minio**.

Verify Blender in converter:

```bash
docker compose exec converter blender --version
# Blender 4.2.x
```

---

## 1. Upload IFC (automated)

```bash
curl -s -X POST http://localhost:5001/upload \
  -F 'file=@./tests/backend/Integration/Fixtures/sample.ifc' \
  -F 'name=IFC AR Test' | jq .
```

**Expected**: `status: "Ready"`, `sourceFormat: "ifc"`, `token`, `shareUrl`, `qrSvg`.

Save `TOKEN` and `PROJECT_ID`.

---

## 2. Upload SKP (automated)

```bash
curl -s -X POST http://localhost:5001/upload \
  -F 'file=@./tests/backend/Integration/Fixtures/sample.skp' \
  -F 'name=SKP AR Test' | jq .
```

**Expected**: `status: "Ready"`, `sourceFormat: "skp"`.

**Failure cases**:
- PDF renamed → `415`
- File > 100 MB → `413`
- Invalid SKP zip → `415`

---

## 3. Verify files on disk

```bash
docker compose exec backend ls -la /data/projects/${PROJECT_ID}/
```

**Expected** (IFC project):
- `original.ifc`, `model.glb`, `model.usdz`, `thumbnail.webp`

**Expected** (SKP project):
- `original.skp`, `model.glb`, `model.usdz`, `thumbnail.webp`

### IFC pipeline

1. IfcConvert → GLB
2. glb_normalize (AR tabletop scale)
3. usd_from_gltf → USDZ
4. Blender render → thumbnail.webp

### SKP pipeline

1. Blender import SKP → export GLB
2. glb_normalize
3. usd_from_gltf → USDZ
4. Blender render → thumbnail.webp

---

## 4. Download assets (automated)

```bash
# GLB
curl -sI "http://localhost:5001/files/${PROJECT_ID}/model.glb" | grep -E 'HTTP|Content-Type|Location'
# 200, model/gltf-binary, no Location

# USDZ
curl -sI "http://localhost:5001/files/${PROJECT_ID}/model.usdz" | grep -E 'HTTP|Content-Type'
# 200, model/vnd.usdz+zip

# Thumbnail
curl -sI "http://localhost:5001/files/${PROJECT_ID}/thumbnail.webp" | grep -E 'HTTP|Content-Type'
# 200, image/webp
```

---

## 5. Share metadata

```bash
curl -s "http://localhost:5001/share/${TOKEN}" | jq .
```

**Expected**: `usdzUrl`, `thumbnailUrl` (`.webp`), same-origin URLs, no MinIO/presign.

---

## 6. Web viewer

Open `https://<host>/s/${TOKEN}`.

**Expected**:
- WebP poster while GLB loads
- Orbit / zoom / fullscreen / auto-rotate
- AR button on mobile (hidden on desktop)
- HTTPS banner if HTTP

---

## 7. Manual AR checklist

| # | Step | Android | iPhone |
|---|---|---|---|
| 1 | Upload IFC via HomePage | ☐ | ☐ |
| 2 | Upload SKP via HomePage | ☐ | ☐ |
| 3 | Web viewer loads (both formats) | ☐ | ☐ |
| 4 | SKP materials visible in viewer | ☐ | ☐ |
| 5 | `ios-src` USDZ in DOM | N/A | ☐ |
| 6 | AR opens (Scene Viewer / Quick Look) | ☐ | ☐ no "Object could not be opened" |
| 7 | QR scan → viewer | ☐ | ☐ |
| 8 | Tabletop scale (~50 cm, parts joined) | ☐ | ☐ |

**iPhone tips**: Safari Network tab — `model.usdz` must be 200, `model/vnd.usdz+zip`, no redirects. Use mkcert for trusted HTTPS (see `app/README.md`).

---

## 8. Automated tests

```bash
dotnet test app/tests/backend/Integration/ -v n
cd app/frontend && npm test
cd app/converter && python -m pytest test_*.py -v
```

---

## 9. Acceptance gate

MVP complete when all pass:

1. ☐ IFC upload → Ready
2. ☐ SKP upload → Ready
3. ☐ `model.glb`, `model.usdz`, `thumbnail.webp` on disk
4. ☐ Assets served direct (200, correct Content-Type, no 3xx)
5. ☐ Android AR works (IFC + SKP)
6. ☐ iPhone Quick Look works (IFC + SKP)
7. ☐ SKP materials recognizable (SC-009)
8. ☐ Zero MinIO references
9. ☐ `docker compose up` brings full stack including Blender
