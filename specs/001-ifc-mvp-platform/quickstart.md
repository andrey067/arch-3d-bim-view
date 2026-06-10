# Quickstart Validation: Arch3DAR — Correção MVP IFC → AR

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> Cenários executáveis que provam o critério de aceitação: GLB + USDZ + AR Android + AR iPhone, sem MinIO.

---

## Prerequisites

| Tool | Min version | Why |
|---|---|---|
| Docker + Docker Compose | 24+ | postgres, backend, converter, frontend+nginx |
| `curl` | any | API smoke tests |
| HTTPS access | TLS cert | AR Quick Look exige HTTPS |
| iPhone (Safari) + Android (Chrome) | iOS 15+ / Android 10+ | Testes AR manuais |
| Sample `.ifc` | ~200 KB | `app/tests/backend/Integration/Fixtures/sample.ifc` |

**Verificar ausência de MinIO**:

```bash
docker compose -f app/docker-compose.yml config --services | grep -i minio
# deve retornar vazio
```

---

## 0. Boot the stack

```bash
cd app
cp .env.example .env
# Definir PUBLIC_BASE_URL=https://<seu-host> (HTTPS obrigatório para AR)
docker compose up -d --build
docker compose ps
```

Serviços esperados: `postgres`, `converter`, `backend`, `frontend`, `nginx` — **sem `minio`**.

```bash
curl -s http://localhost:5001/health
# {"status":"ok"}
```

---

## 1. Upload IFC (automated)

```bash
curl -s -X POST http://localhost:5001/upload \
  -F 'file=@./tests/backend/Integration/Fixtures/sample.ifc' \
  -F 'name=AR Test Model' | jq .
```

**Expected**:
- `status`: `"Ready"`
- `token`: 32-char hex
- `shareUrl`: URL com `/s/{token}`
- `qrSvg`: SVG não vazio

Salvar `TOKEN` e `PROJECT_ID` da resposta.

**Failure cases**:
- PDF renomeado → `415`
- Arquivo > 100 MB → `413`

---

## 2. Verify files on disk

```bash
docker compose exec backend ls -la /data/projects/${PROJECT_ID}/
```

**Expected files**:
- `original.ifc`
- `model.glb` (size > 0)
- `model.usdz` (size > 0)
- `thumbnail.png`

---

## 3. Download GLB and USDZ (automated)

```bash
# GLB
curl -sI "http://localhost:5001/files/${PROJECT_ID}/model.glb" | grep -E 'HTTP|Content-Type|Location'
# HTTP/1.1 200
# Content-Type: model/gltf-binary
# (no Location header)

curl -s -o /tmp/test.glb "http://localhost:5001/files/${PROJECT_ID}/model.glb"
file /tmp/test.glb
# GLB binary

# USDZ
curl -sI "http://localhost:5001/files/${PROJECT_ID}/model.usdz" | grep -E 'HTTP|Content-Type|Location'
# HTTP/1.1 200
# Content-Type: model/vnd.usdz+zip

curl -s -o /tmp/test.usdz "http://localhost:5001/files/${PROJECT_ID}/model.usdz"
unzip -l /tmp/test.usdz
# lista entradas USD válidas
```

---

## 4. Share metadata (automated)

```bash
curl -s "http://localhost:5001/share/${TOKEN}" | jq .
```

**Expected**:
- `usdzUrl` non-null, same host as `glbUrl`
- URLs apontam para `/files/{projectId}/model.glb` e `model.usdz`
- Nenhuma URL contém `minio`, `X-Amz`, ou porta `9000`

---

## 5. Web viewer

Abrir `https://<host>/s/${TOKEN}` (via HTTPS).

**Expected**:
- Thumbnail visível como poster
- Modelo 3D carrega (orbit/zoom)
- Botão AR visível em mobile
- Se HTTP: banner "AR requires HTTPS"

---

## 6. Manual AR checklist

| # | Step | Android (Chrome) | iPhone (Safari) |
|---|---|---|---|
| 1 | Upload IFC via HomePage | ☐ | ☐ |
| 2 | GLB gerado (viewer carrega) | ☐ | ☐ |
| 3 | USDZ gerado (`ios-src` no DOM) | N/A | ☐ |
| 4 | Abrir Viewer Web | ☐ | ☐ |
| 5 | Tap "View in your space" / AR | ☐ Scene Viewer abre | ☐ Quick Look abre **sem** "Object could not be opened" |
| 6 | Escanear QR Code (Android) | ☐ | N/A |
| 7 | Escanear QR Code (iPhone) | N/A | ☐ |
| 8 | Modelo ancorado em escala real | ☐ | ☐ |

**iPhone debug tips**:
- Safari Web Inspector → Network: `model.usdz` deve ser `200`, `model/vnd.usdz+zip`, sem redirect chain.
- Confirmar `ios-src` attribute no `<model-viewer>` via Elements panel.

---

## 7. Automated test commands

```bash
# Backend integration (from repo root)
dotnet test app/tests/backend/Integration/ -v n

# Frontend unit
cd app/frontend && npm test
```

Testes devem cobrir:
- Upload → Ready
- GLB/USDZ download com Content-Type
- Share response inclui `usdzUrl`

---

## 8. Acceptance gate

O MVP correção está **concluído** quando todos passam:

1. ☐ IFC upload via `POST /upload`
2. ☐ `model.glb` gerado e servido com `model/gltf-binary`
3. ☐ `model.usdz` gerado e servido com `model/vnd.usdz+zip`
4. ☐ QR Code acessível
5. ☐ Android AR funciona
6. ☐ iPhone AR funciona sem erro Quick Look
7. ☐ Zero referências MinIO em compose, código e env
8. ☐ Assets servidos diretamente (sem redirect 3xx)
