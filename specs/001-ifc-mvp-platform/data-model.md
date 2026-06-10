# Data Model: Arch3DAR — Correção MVP

**Phase**: 1
**Branch**: `main`
**Date**: 2026-06-10
**Plan**: `specs/001-ifc-mvp-platform/plan.md`
**Research**: `specs/001-ifc-mvp-platform/research.md`

> Modelo simplificado: uma tabela `projects`, arquivos no disco local. Sem `ShareLinks`, sem Identity, sem MinIO keys.

---

## ER overview

```
┌──────────────┐
│   Project    │
│  (postgres)  │
└──────┬───────┘
       │ 1:1 paths
       ▼
┌──────────────┐
│  Local files │  /data/projects/{id}/
│  (filesystem)│  original.ifc, model.glb, model.usdz, thumbnail.png
└──────────────┘
```

---

## Entity: `Project` (table `projects`)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `Id` | `uuid` | PK, default `gen_random_uuid()` | Identificador interno. Usado em `/files/{id}/...`. |
| `PublicToken` | `varchar(32)` | NOT NULL, **unique** | Token hex 32 chars (128 bits). URL: `/s/{token}`. |
| `Name` | `varchar(200)` | NOT NULL | Nome exibido no viewer. |
| `Status` | `varchar(16)` | NOT NULL | `Uploading`, `Converting`, `Ready`, `Failed`. |
| `ErrorMessage` | `varchar(500)` | NULL | Motivo legível quando `Failed`. |
| `DataDirectory` | `varchar(512)` | NOT NULL | Path relativo: `projects/{id}`. |
| `IfcFileName` | `varchar(64)` | NOT NULL, default `original.ifc` | Nome fixo no diretório. |
| `GlbFileName` | `varchar(64)` | NULL, default `model.glb` | Preenchido quando Ready. |
| `UsdzFileName` | `varchar(64)` | NULL, default `model.usdz` | **Obrigatório** quando Ready. |
| `ThumbnailFileName` | `varchar(64)` | NULL, default `thumbnail.png` | Preenchido quando Ready. |
| `IfcSizeBytes` | `bigint` | NOT NULL | Tamanho do upload. |
| `ConversionDurationMs` | `bigint` | NULL | Duração total IFC→GLB→USDZ. |
| `CreatedAt` | `timestamptz` | NOT NULL | |
| `UpdatedAt` | `timestamptz` | NOT NULL | |

**Indexes**:
- PK `Id`
- Unique `PublicToken` (lookup público)
- Index `Status` (opcional, monitoramento)

**Removed columns** (vs. plano anterior):
- `OwnerId`, `Description`, `ClientLabel`, `IfcObjectKey`, `GlbObjectKey`, `UsdzObjectKey`, `ThumbnailObjectKey` (MinIO keys)
- `PublishedAt`, `ConversionStartedAt` (sem publish em duas etapas)

---

## State machine

```
┌─────────────┐
│  Uploading  │  (IFC sendo gravado em disco)
└──────┬──────┘
       │ IFC salvo, conversão iniciada
       ▼
┌─────────────┐
│ Converting  │  (IfcConvert + usd_from_gltf)
└──────┬──────┘
  ok   │   fail
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌────────┐
│ Ready│ │ Failed │
└──────┘ └────────┘
```

- `Ready` exige `model.glb`, `model.usdz` e `thumbnail.png` existentes no disco.
- Não há estado `Published` separado — upload bem-sucedido já gera link público.

---

## Filesystem layout

| Arquivo | Path absoluto | Content-Type (HTTP) | Público |
|---|---|---|---|
| IFC original | `/data/projects/{id}/original.ifc` | — | Não |
| GLB | `/data/projects/{id}/model.glb` | `model/gltf-binary` | Sim |
| USDZ | `/data/projects/{id}/model.usdz` | `model/vnd.usdz+zip` | Sim |
| Thumbnail | `/data/projects/{id}/thumbnail.png` | `image/png` | Sim |

**Validation rules**:
- Diretório criado atomicamente antes da escrita do IFC.
- GLB e USDZ devem ter `length > 0` após conversão.
- USDZ deve ser ZIP válido contendo assets USD (verificado no teste de integração).

---

## DTOs

### `UploadResponse` (`POST /upload` → 200)

```json
{
  "token": "a1b2c3d4e5f6...",
  "projectId": "8b7e4f1a-1c2d-4e3f-9a5b-6c7d8e9f0a1b",
  "name": "Living Room Sofa",
  "status": "Ready",
  "shareUrl": "https://app.example.com/s/a1b2c3d4...",
  "qrSvg": "<svg>...</svg>"
}
```

### `ShareDto` (`GET /share/{token}` → 200)

```json
{
  "name": "Living Room Sofa",
  "status": "Ready",
  "glbUrl": "https://app.example.com/files/8b7e4f1a-.../model.glb",
  "usdzUrl": "https://app.example.com/files/8b7e4f1a-.../model.usdz",
  "thumbnailUrl": "https://app.example.com/files/8b7e4f1a-.../thumbnail.png"
}
```

**Not exposed**: `projectId` no JSON público (opcional — pode usar token-only URLs se preferir ocultar UUID; MVP usa projectId em `/files/` por simplicidade).

### Error states

| Status project | GET /share/{token} |
|---|---|
| `Converting` | 200 com `status: "Converting"`, URLs null |
| `Failed` | 404 (não expor erro interno) |
| token inválido | 404 |

---

## Migrations

Single migration `20260610000000_Initial.cs` (ou replace):
- Tabela `projects` com colunas acima.
- Drop `share_links` se existir.
- Drop tabelas Identity se removidas.

`EnsureCreated()` ou `Migrate()` no startup do backend.
