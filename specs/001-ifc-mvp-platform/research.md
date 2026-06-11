# Research: Arch3DAR — IFC/SketchUp → Web 3D + AR MVP

**Phase**: 0
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`

> Decisões técnicas para MVP simplificado: IFC + DAE/OBJ (fluxo SketchUp), storage local, USDZ Quick Look, Blender headless, thumbnail WebP. R-11…R-17 da correção permanecem válidos onde não conflitam; R-19 **supersedido** por R-21 (clarificação 2026-06-10).

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
    thumbnail.webp
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
- **Ordem no pipeline**: `IfcConvert` → **`glb_normalize`** (R-18) → `usd_from_gltf` → thumbnail. O USDZ reflete o GLB já normalizado para AR tabletop.
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
  | `.webp` | `image/webp` |
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
    ar-placement="floor"
    camera-controls
    shadow-intensity="1"
    exposure="1"
    auto-rotate
    poster={thumbnailUrl}
  />
  ```
- `ios-src` **só é definido** quando `usdzUrl` é non-null e projeto `ready`.
- `ar-modes` com `quick-look` **primeiro** — prioriza iOS.
- `ar-placement="floor"` — modelo normalizado com `min(Y)=0` ancora em superfície detectada (mesa/chão).
- Fallback iOS: `<a rel="ar" href={usdzUrl}>` quando o botão AR do model-viewer falha.
- **Sem** `camera-target` fixo — deixa o model-viewer enquadrar o modelo tabletop.
- API `GET /share/{token}` retorna:
  ```json
  {
    "name": "...",
    "glbUrl": "https://host/files/{projectId}/model.glb",
    "usdzUrl": "https://host/files/{projectId}/model.usdz",
    "thumbnailUrl": "https://host/files/{projectId}/thumbnail.webp"
  }
  ```
- URLs devem ser **absolutas** e **HTTPS** em produção (`PUBLIC_BASE_URL`).

**Rationale**
- [model-viewer AR docs](https://modelviewer.dev/docs/faq.html): iOS requer `ios-src` com USDZ; `src` GLB sozinho não ativa Quick Look corretamente.
- [Apple Quick Look](https://developer.apple.com/augmented-reality/quick-look/): asset deve ser USDZ servido com MIME correto, sem redirect, via HTTPS.

**Alternatives considered**
- **Apenas `src` GLB com `ar-modes` incluindo quick-look**: insuficiente — comportamento atual que falha no iPhone.
- **Link `<a rel="ar" href="...usdz">` separado**: adotado como fallback iOS no MVP após testes em dispositivo real.

---

## R-18. Normalização GLB para AR tabletop (`glb_normalize`)

**Decision**
- Após `IfcConvert`, executar `normalize_glb_for_ar(glb_path, max_extent_m)` em `glb_normalize.py` **antes** de `usd_from_gltf`.
- Variável de ambiente `AR_MAX_EXTENT_M` (default **0.5** m) — maior dimensão do bounding box após normalização.
- Passos (in-place no `model.glb`):
  1. **Bake matrices**: para cada nó com `matrix` 4×4, multiplicar vértices POSITION da mesh filha; remover `matrix` dos nós.
  2. **Scale uniforme**: `scale = max_extent_m / max(width, height, depth)` sobre o assembly completo.
  3. **Center X/Z**: origem horizontal no centro do modelo.
  4. **Floor Y**: transladar para `min(Y) = 0` — base apoiada na superfície em Quick Look / Scene Viewer.

**Rationale**
- IfcConvert emite **vários nós** com matrizes de translação (dezenas de metros). Escalar só vértices locais sem aplicar matrizes faz as peças **separarem** em AR (bug observado em produção).
- Edifícios IFC típicos têm ~20 m de extensão; `ar-scale="auto"` do model-viewer **não** redimensiona o `ios-src` USDZ no iOS — a escala deve estar baked no asset.
- Tabletop (~50 cm) cabe em mesa e evita colisão com paredes reais da sala.

**Alternatives considered**
- **Só `ar-scale="auto"` no model-viewer**: rejeitado — não afeta USDZ no Quick Look.
- **IfcConvert com merge de geometria**: não disponível de forma confiável; bake de matrizes resolve sem reexportar IFC.
- **Escala em USDZ pós-conversão**: rejeitado — duplicaria lógica; GLB normalizado alimenta web viewer e USDZ.

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
  | GET | `/files/{projectId}/thumbnail.webp` | stream WebP |
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
  2. Assert files exist on disk: `model.glb`, `model.usdz`, `thumbnail.webp`.
  3. GET `/files/{id}/model.glb` → 200, `Content-Type: model/gltf-binary`, no `Location` header.
  4. GET `/files/{id}/model.usdz` → 200, `Content-Type: model/vnd.usdz+zip`.
  5. GET `/share/{token}` → `usdzUrl` non-null, same-origin paths.
- `UsdConverterTests` (converter): GLB fixture → USDZ > 0 bytes, zip abre com entradas USD.
- Remover Testcontainers MinIO fixture.

**Rationale**
- Critérios de aceitação do usuário exigem testes de upload, conversão GLB/USDZ e download.
- Assert de ausência de redirect é específico ao bug iOS.

---

## R-19. SKP → GLB (Blender headless) — **SUPERSEDED**

> **Status**: Obsoleto (2026-06-10). Blender 4.2.3 stock **não inclui** `io_sketchup` nem `bpy.ops.import_scene.skp`. O Dockerfile não instala addon. Ver **R-21**.

---

## R-21. SketchUp workflow: DAE/OBJ upload → GLB (Blender headless)

**Decision**
- Pipeline primário (clarificação 2026-06-10): usuários SketchUp exportam **Collada (`.dae`, primário)** ou **Wavefront (`.obj`)**; upload direto de `.skp` **proibido**.
- Script `mesh_to_glb.py` invocado via:
  ```bash
  blender -b --python mesh_to_glb.py -- \
    --input /data/projects/{id}/original.dae \
    --output /data/projects/{id}/model.glb \
    --format dae
  ```
  (ou `--format obj` para `original.obj`)
- Blender operators: `bpy.ops.import_scene.dae` / `bpy.ops.import_scene.obj` — **nativos** no Blender 4.2, sem addon.
- Após export GLB, pipeline comum: `glb_normalize` → `usd_from_gltf` → thumbnail.
- Validação upload:
  | Format | Extension | Signature |
  |---|---|---|
  | DAE | `.dae` | XML com root `<COLLADA` ou `<?xml` + `COLLADA` namespace |
  | OBJ | `.obj` | Texto com linhas `v ` / `f ` (best-effort) |
  | SKP | `.skp` | **Rejeitar 415** com mensagem: exportar Collada do SketchUp |
- Timeout dedicado: `MESH_CONVERSION_TIMEOUT_S=180` (renomear de `SKP_CONVERSION_TIMEOUT_S`).
- Upload UI: `accept=".ifc,.dae,.obj"` + instruções SketchUp export (FR-001a).

**Rationale**
- Produção validada: Collada import funciona no container atual sem dependências extras.
- Materiais/texturas SketchUp preservados razoavelmente via export DAE (melhor que Assimp SKP).
- Evita addons pagos/instáveis (`SketchUp Importer`) e pipeline ODA (não open source).
- Mesmo runtime Blender serve thumbnail (R-20).

**Alternatives considered**
- **Blender native SKP import (`io_sketchup`)**: rejeitado — **não existe** no Blender oficial 4.2.3 linux-x64; falha com "SKP import operator unavailable".
- **Third-party SketchUp Importer addon**: rejeitado — manutenção frágil, alguns pagos, quebra entre versões Blender.
- **ODA SKP → DAE**: rejeitado — deixa de ser totalmente open source.
- **Assimp CLI para SKP**: rejeitado — suporte SKP limitado, materiais degradados.

**Linux Docker note**
- Blender 4.2 tarball oficial (amd64) no Dockerfile — **sem** instalação de addon SKP.
- Dependências: `libgl1`, `libglib2.0-0`, `libxi6`, `libxxf86vm1` (já presentes).
- Fixture de teste: `.dae` exportado do SketchUp 2023+ (não `.skp`).

---

## R-20. Thumbnail WebP (Blender headless)

**Decision**
- Formato: **`thumbnail.webp`** (clarificação SpecDrive).
- Geração via `render_thumbnail.py` no Blender (mesmo container):
  ```bash
  blender -b --python render_thumbnail.py -- \
    --input /data/projects/{id}/model.glb \
    --output /data/projects/{id}/thumbnail.webp \
    --size 512
  ```
- Cena: import GLB, câmera isométrica, luz área, fundo neutro, render Cycles ou EEVEE (EEVEE preferido por velocidade headless).
- Fallback IFC-only (transição): IfcConvert `--thumbnail` → PNG convertido para WebP via Pillow até Phase C completar Blender para todos os formatos.
- HTTP: `Content-Type: image/webp`.

**Rationale**
- WebP ~30% menor que PNG — melhora SC-003 (4G, poster first).
- Blender render produz preview visualmente alinhado ao modelo 3D (materiais), superior a placeholder IfcConvert.
- Unifica pipeline IFC e DAE/OBJ no mesmo gerador de thumbnail.

**Alternatives considered**
- **Pillow placeholder**: rejeitado como destino final — não reflete materiais DAE/OBJ.
- **PNG + nginx content negotiation**: rejeitado — clarificação fixou WebP.
- **glTF screenshot via headless Chrome**: rejeitado — complexidade desnecessária.

---

## Cross-cutting summary (IFC/SketchUp MVP)

| Concern | Choice |
|---|---|
| Input formats | **`.ifc`** (IfcConvert) + **`.dae`/`.obj`** (Blender Collada/OBJ); **`.skp` rejeitado** |
| Object storage | **Local filesystem** `/data/projects/{id}/` |
| GLB delivery | Backend `Results.File`, same-origin, GET+HEAD |
| GLB normalization | **`glb_normalize`** bake matrices + tabletop scale (`AR_MAX_EXTENT_M`) |
| USDZ generation | **Google `usd_from_gltf`** on normalized GLB |
| Thumbnail | **`thumbnail.webp`** via Blender headless render |
| Converter topology | **Single sidecar** (IfcOpenShell + Blender + USDZ) |
| iOS AR | `ios-src` + `rel="ar"` fallback + `model/vnd.usdz+zip` + HTTPS + no redirect |
| Android AR | `src` GLB + `scene-viewer` mode |
| Auth | **None** (MVP) |
| Queue | **None** (synchronous convert on upload) |
| Docker services | postgres, converter, backend, frontend+nginx (4) |

**Zero open `NEEDS CLARIFICATION` markers remain.**
