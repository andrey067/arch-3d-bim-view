# Data Model: Arch3DAR — IFC/SKP MVP

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`
**Research**: `specs/001-ifc-mvp-platform/research.md`

> Uma tabela `projects`, arquivos no disco local. Sem auth, sem ShareLinks table, sem MinIO.

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
│  (filesystem)│  original.ifc|skp, model.glb, model.usdz, thumbnail.webp
└──────────────┘
```

---

## Entity: `Project` (table `projects`)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `Id` | `uuid` | PK, default `gen_random_uuid()` | Identificador interno. Usado em `/files/{id}/...`. |
| `PublicToken` | `varchar(32)` | NOT NULL, **unique** | Token hex 32 chars (128 bits). URL: `/s/{token}`. |
| `Name` | `varchar(200)` | NOT NULL | Nome exibido no viewer. |
| `SourceFormat` | `varchar(8)` | NOT NULL | `ifc` \| `skp`. |
| `Status` | `varchar(16)` | NOT NULL | `Uploading`, `Converting`, `Ready`, `Failed`. |
| `ErrorMessage` | `varchar(500)` | NULL | Motivo legível quando `Failed`. |
| `DataDirectory` | `varchar(512)` | NOT NULL | Path relativo: `projects/{id}`. |
| `OriginalFileName` | `varchar(64)` | NOT NULL | `original.ifc` ou `original.skp`. |
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

---

## State machine

```
┌─────────────┐
│  Uploading  │  (original being written)
└──────┬──────┘
       │ saved, conversion started
       ▼
┌─────────────┐
│ Converting  │  (IfcConvert OR Blender → normalize → USDZ → thumbnail)
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
| Original SKP | `/data/projects/{id}/original.skp` | — | Não |
| GLB | `/data/projects/{id}/model.glb` | `model/gltf-binary` | Sim |
| USDZ | `/data/projects/{id}/model.usdz` | `model/vnd.usdz+zip` | Sim |
| Thumbnail | `/data/projects/{id}/thumbnail.webp` | `image/webp` | Sim |

**Validation rules**:
- Diretório criado antes da escrita do original.
- GLB, USDZ, WebP devem ter `length > 0`.
- USDZ deve ser ZIP válido (teste integração).
- SKP upload: ZIP magic + estrutura SketchUp (ver R-19).

---

## DTOs

### `UploadResponse` (`POST /upload` → 200)

```json
{
  "token": "a1b2c3d4e5f6...",
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Kitchen Island",
  "sourceFormat": "skp",
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
  "sourceFormat": "skp",
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

---

## Migrations

Migration `20260610000001_AddSourceFormatAndWebpThumbnail.cs`:
- Add `SourceFormat varchar(8) NOT NULL DEFAULT 'ifc'`
- Rename `IfcFileName` → `OriginalFileName` (or add column + backfill)
- Update default `ThumbnailFileName` to `thumbnail.webp`
