# Data Model: Arch3DAR — IFC/SketchUp MVP

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`
**Research**: `specs/001-ifc-mvp-platform/research.md`

> Uma tabela `projects`, arquivos no disco local. Sem auth, sem ShareLinks table, sem MinIO. SketchUp via DAE/OBJ export — sem `.skp`.

---

## ER overview

```
┌──────────────┐
│   Project    │
│  (postgres)  │
│ source_format│
└──────┬───────┘
       │ 1:1 paths
       ▼
┌──────────────┐
│  Local files │  /data/projects/{id}/
│  (filesystem)│  original.ifc|dae|obj, model.glb, model.usdz, thumbnail.webp
└──────────────┘
```

---

## Entity: `Project` (table `projects`)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `Id` | `uuid` | PK, default `gen_random_uuid()` | Identificador interno. Usado em `/files/{id}/...`. |
| `PublicToken` | `varchar(32)` | NOT NULL, **unique** | Token hex 32 chars (128 bits). URL: `/s/{token}`. |
| `Name` | `varchar(200)` | NOT NULL | Nome exibido no viewer. |
| `SourceFormat` | `varchar(8)` | NOT NULL | `ifc` \| `dae` \| `obj`. |
| `Status` | `varchar(16)` | NOT NULL | `Uploading`, `Converting`, `Ready`, `Failed`. |
| `ErrorMessage` | `varchar(500)` | NULL | Motivo legível quando `Failed`. |
| `DataDirectory` | `varchar(512)` | NOT NULL | Path relativo: `projects/{id}`. |
| `OriginalFileName` | `varchar(64)` | NOT NULL | `original.ifc`, `original.dae`, ou `original.obj`. |
| `GlbFileName` | `varchar(64)` | NULL, default `model.glb` | Preenchido quando Ready. |
| `UsdzFileName` | `varchar(64)` | NULL, default `model.usdz` | **Obrigatório** quando Ready. |
| `ThumbnailFileName` | `varchar(64)` | NULL, default `thumbnail.webp` | Preenchido quando Ready. |
| `OriginalSizeBytes` | `bigint` | NOT NULL | Tamanho do upload. |
| `ConversionDurationMs` | `bigint` | NULL | Duração total conversão. |
| `CreatedAt` | `timestamptz` | NOT NULL | |
| `UpdatedAt` | `timestamptz` | NOT NULL | |

**Indexes**:
- PK `Id`
- Unique `PublicToken`
- Index `Status` (opcional)

**Removed / deferred** (vs. spec original):
- `OwnerId`, tenant columns, MinIO object keys, `PublishedAt`, publish workflow
- `source_format = skp` — obsoleto; `.skp` não é aceito

---

## State machine

```
┌─────────────┐
│  Uploading  │  (original being written)
└──────┬──────┘
       │ saved, conversion started
       ▼
┌─────────────┐
│ Converting  │  (IfcConvert OR Blender DAE/OBJ → normalize → USDZ → thumbnail)
└──────┬──────┘
  ok   │   fail
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌────────┐
│ Ready│ │ Failed │
└──────┘ └────────┘
```

- `Ready` exige `model.glb`, `model.usdz`, `thumbnail.webp` no disco com size > 0.
- Link público disponível imediatamente ao atingir `Ready`.

---

## Filesystem layout

| Arquivo | Path | Content-Type (HTTP) | Público |
|---|---|---|---|
| Original IFC | `/data/projects/{id}/original.ifc` | — | Não |
| Original DAE | `/data/projects/{id}/original.dae` | — | Não |
| Original OBJ | `/data/projects/{id}/original.obj` | — | Não |
| GLB | `/data/projects/{id}/model.glb` | `model/gltf-binary` | Sim |
| USDZ | `/data/projects/{id}/model.usdz` | `model/vnd.usdz+zip` | Sim |
| Thumbnail | `/data/projects/{id}/thumbnail.webp` | `image/webp` | Sim |

**Validation rules**:
- Diretório criado antes da escrita do original.
- GLB, USDZ, WebP devem ter `length > 0`.
- USDZ deve ser ZIP válido (teste integração).
- DAE upload: XML com elemento `COLLADA` (ver R-21).
- OBJ upload: formato texto Wavefront com vértices/faces.
- **SKP upload**: rejeitar antes de persistir; mensagem com instruções export Collada.

---

## DTOs

### `UploadResponse` (`POST /upload` → 200)

```json
{
  "token": "a1b2c3d4e5f6...",
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Kitchen Island",
  "sourceFormat": "dae",
  "status": "Ready",
  "shareUrl": "https://app.example.com/s/a1b2c3d4...",
  "qrSvg": "<svg>...</svg>"
}
```

### `ShareDto` (`GET /share/{token}` → 200)

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

### Error states

| Status project | GET /share/{token} |
|---|---|
| `Converting` | 200 com `status: "Converting"`, URLs null |
| `Failed` | 404 |
| token inválido | 404 |

### SKP rejection (`POST /upload` → 415)

```json
{
  "type": "https://arch3dar.com/errors/unsupported-format",
  "title": "SketchUp .skp not supported",
  "status": 415,
  "detail": "Export your model from SketchUp as Collada (.dae): File → Export → 3D Model → Collada, then upload the .dae file."
}
```

---

## Migrations

Migration `20260610130000_AddSourceFormat.cs` (update):
- `SourceFormat` enum values: `ifc`, `dae`, `obj` (remove `skp` if present)
- `OriginalFileName` supports `original.dae`, `original.obj`
- Default `ThumbnailFileName` = `thumbnail.webp`
