# Research: Arch3DAR — Correção MVP IFC → AR

**Phase**: 0
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> Resolve decisões técnicas para Quick Look iOS, remoção de MinIO e pipeline USDZ. Substitui decisões R-02, R-06 parcial, R-08, R-10 do research anterior onde conflitam.

---

## R-11. Armazenamento local (substitui R-02 MinIO)

**Decision**
- Volume Docker `project_data` montado em `/data` nos containers `backend` e `converter`.
- Layout por projeto:
  ```
  /data/projects/{projectId}/
    original.ifc
    model.glb
    model.usdz
    thumbnail.png
  ```
- Backend expõe arquivos via `GET /files/{projectId}/model.glb` (e variantes) usando `Results.File(path, contentType)` — **sem redirect**, **sem presigned URL**.
- `LocalFileStorage` encapsula create-dir, write-bytes, resolve-path, exists-check. Paths relativos (`projects/{id}/model.glb`) persistidos na tabela `projects`.

**Rationale**
- Quick Look no iOS falha frequentemente com redirects (302/307/308) e URLs cross-origin presigned (MinIO em host/porta diferente do SPA).
- Servir do mesmo origin (`https://dominio.com/files/...`) satisfaz requisitos de HTTPS, mixed content e estabilidade do Quick Look.
- YAGNI: um volume local é suficiente para MVP single-node; elimina MinIO (serviço + SDK + políticas + presign TTL).

**Alternatives considered**
- **MinIO com proxy same-origin**: ainda adiciona hop e risco de redirect mal configurado; rejeitado.
- **Nginx `alias` direto para `/data`**: válido em prod, mas duplica lógica de auth/404; backend como único gatekeeper de metadados é mais simples no MVP.
- **SQLite em vez de Postgres**: possível, mas migração desnecessária — Postgres já roda.

---

## R-12. GLB → USDZ (`UsdConverter`)

**Decision**
- **Ferramenta primária: Google `usd_from_gltf`** — CLI nativa C++, projetada para AR Quick Look, 10–15× mais rápida que alternativas scriptadas, lê GLB binário e emite USDZ.
- Implementação no converter:
  ```python
  # usd_converter.py
  def glb_to_usdz(glb_path: str, usdz_path: str) -> None:
      subprocess.run(
          ["usd_from_gltf", glb_path, usdz_path],
          check=True, timeout=CONVERSION_TIMEOUT_S,
      )
  ```
- Dockerfile do converter: multi-stage build com `usd_from_gltf` pré-compilado (base `marlon360/usd-from-gltf` ou build from source no CI) + IfcOpenShell.
- **USDZ é obrigatório**: se `usd_from_gltf` falhar ou produzir arquivo vazio, a conversão inteira falha com `422` — não há fallback GLB-only para iOS.

**Rationale**
- A implementação atual (trimesh + OpenUSD manual → zip com `.usda`) produz USDZ tecnicamente válido como zip mas **incompatível** com Quick Look (falta estrutura/material/escala esperada pelo viewer Apple).
- `usd_from_gltf` é a ferramenta recomendada pela comunidade model-viewer e documentação Apple para transmissão USDZ.
- Blender headless: ~1.5 GB imagem, startup lento, overkill para conversão one-way.
- `usdzconvert` (macOS only): incompatível com Linux Docker.
- Pixar USD toolchain puro: correto mas sem caminho glTF nativo — `usd_from_gltf` já empacota USD + glTF reader.

**Alternatives considered**
- **trimesh + pxr (atual)**: rejeitado — causa erro Quick Look observado em produção.
- **Blender 4.x batch export USDZ**: rejeitado — imagem pesada, CI lento, operação frágil.
- **Serviço externo gltf2usdz.online**: rejeitado — dependência de rede, viola self-hosted MVP.

---

## R-13. Content-Type e entrega HTTP

**Decision**
- Middleware `ModelContentTypeMiddleware` (ou `StaticFileOptions.OnPrepareResponse`) define:
  | Extensão | Content-Type |
  |---|---|
  | `.glb` | `model/gltf-binary` |
  | `.usdz` | `model/vnd.usdz+zip` |
  | `.png` | `image/png` |
  | `.ifc` | `application/octet-stream` (não exposto publicamente no MVP) |
- Headers adicionais: `Accept-Ranges: bytes` (GLB streaming para model-viewer).
- **Proibido**: `return Redirect()`, presigned redirect, `proxy_redirect` no nginx.
- nginx `location /files/`:
  ```nginx
  location /files/ {
      proxy_pass http://backend:5000/files/;
      proxy_redirect off;
      proxy_set_header Host $host;
  }
  ```

**Rationale**
- Apple Quick Look valida MIME type; `application/octet-stream` ou `application/zip` genérico causa falha.
- model-viewer usa range requests no GLB; `Accept-Ranges` melhora carregamento.

**Alternatives considered**
- **Deixar Kestrel inferir por extensão**: insuficiente — `.usdz` não está no mapa default do ASP.NET.

---

## R-14. model-viewer + Quick Look (iOS)

**Decision**
- Configuração obrigatória no `SharePage`/`ViewerPage`:
  ```tsx
  <model-viewer
    src={glbUrl}
    ios-src={usdzUrl}
    ar
    ar-modes="quick-look scene-viewer webxr"
    camera-controls
    shadow-intensity="1"
    exposure="1"
    auto-rotate
    poster={thumbnailUrl}
  />
  ```
- `ios-src` **só é definido** quando `usdzUrl` é non-null e projeto `ready`.
- `ar-modes` com `quick-look` **primeiro** — prioriza iOS.
- API `GET /share/{token}` retorna:
  ```json
  {
    "name": "...",
    "glbUrl": "https://host/files/{projectId}/model.glb",
    "usdzUrl": "https://host/files/{projectId}/model.usdz",
    "thumbnailUrl": "https://host/files/{projectId}/thumbnail.png"
  }
  ```
- URLs devem ser **absolutas** e **HTTPS** em produção (`PUBLIC_BASE_URL`).

**Rationale**
- [model-viewer AR docs](https://modelviewer.dev/docs/faq.html): iOS requer `ios-src` com USDZ; `src` GLB sozinho não ativa Quick Look corretamente.
- [Apple Quick Look](https://developer.apple.com/augmented-reality/quick-look/): asset deve ser USDZ servido com MIME correto, sem redirect, via HTTPS.

**Alternatives considered**
- **Apenas `src` GLB com `ar-modes` incluindo quick-look**: insuficiente — comportamento atual que falha no iPhone.
- **Link `<a rel="ar" href="...usdz">` separado**: redundante quando `ios-src` está correto; manter como fallback opcional pós-MVP.

---

## R-15. Simplificação de API e remoção de auth

**Decision**
- Endpoints públicos (sem cookie/JWT):
  | Método | Path | Função |
  |---|---|---|
  | POST | `/upload` | multipart `file` + opcional `name` → converte inline, retorna token + shareUrl + qrSvg |
  | GET | `/share/{token}` | metadados + URLs absolutas dos assets |
  | GET | `/files/{projectId}/model.glb` | stream GLB |
  | GET | `/files/{projectId}/model.usdz` | stream USDZ |
  | GET | `/files/{projectId}/thumbnail.png` | stream PNG |
  | GET | `/share/{token}/qr` ou `/qrcode/{token}` | SVG QR |
  | GET | `/health` | liveness |
- Frontend: `HomePage` (upload) + `SharePage` (viewer em `/s/:token`).
- Remover: Identity, dashboard, `POST /api/projects`, publish em duas etapas, `ShareLinks` table.

**Rationale**
- Usuário explicitamente pediu remoção de auth/dashboard/multi-tenant para focar em AR.
- Upload síncrono (backend aguarda converter) simplifica estado — sem fila Postgres.

**Alternatives considered**
- **Manter auth só para upload**: rejeitado — escopo pede remoção completa.
- **Conversão assíncrona com polling**: rejeitado — adiciona UX sem benefício no MVP single-user.

---

## R-16. Docker Compose (substitui R-10)

**Decision**
- **4 serviços**:
  1. `postgres` — metadados
  2. `converter` — IfcConvert + usd_from_gltf, volume `/data`
  3. `backend` — API + file serving, volume `/data`
  4. `frontend` + `nginx` — SPA + TLS + reverse proxy
- **Removido**: `minio`, `minio_data` volume.
- Variáveis novas: `DATA_ROOT=/data`, `PUBLIC_BASE_URL=https://...`.

**Rationale**
- Menos serviços = menos pontos de falha para Quick Look.
- Volume compartilhado evita HTTP hop converter→backend para bytes (converter escreve, backend lê).

---

## R-17. Testes automatizados

**Decision**
- `UploadAndConvertTests` (integration):
  1. POST `/upload` com `sample.ifc` → 200, `status=Ready`.
  2. Assert files exist on disk: `model.glb`, `model.usdz`, `thumbnail.png`.
  3. GET `/files/{id}/model.glb` → 200, `Content-Type: model/gltf-binary`, no `Location` header.
  4. GET `/files/{id}/model.usdz` → 200, `Content-Type: model/vnd.usdz+zip`.
  5. GET `/share/{token}` → `usdzUrl` non-null, same-origin paths.
- `UsdConverterTests` (converter): GLB fixture → USDZ > 0 bytes, zip abre com entradas USD.
- Remover Testcontainers MinIO fixture.

**Rationale**
- Critérios de aceitação do usuário exigem testes de upload, conversão GLB/USDZ e download.
- Assert de ausência de redirect é específico ao bug iOS.

---

## Cross-cutting summary (correction)

| Concern | Choice |
|---|---|
| Object storage | **Local filesystem** `/data/projects/{id}/` |
| GLB delivery | Backend `Results.File`, same-origin |
| USDZ generation | **Google `usd_from_gltf`** in converter |
| iOS AR | `ios-src` + `model/vnd.usdz+zip` + HTTPS + no redirect |
| Android AR | `src` GLB + `scene-viewer` mode |
| Auth | **None** (MVP correction) |
| Queue | **None** (synchronous convert on upload) |
| Docker services | postgres, converter, backend, frontend+nginx (4) |

**Zero open `NEEDS CLARIFICATION` markers remain.**
