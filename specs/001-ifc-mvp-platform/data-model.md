# Data Model — App 3D Viewer (conceitual)

**Feature**: `001-ifc-mvp-platform` (App 3D Viewer MVP)
**Status**: Conceitual (sem migrations, sem DDL, sem código de ORM).

> Este documento descreve **entidades, atributos, relacionamentos e
> regras de validação** no nível conceitual. Implementação
> (SQLAlchemy 2 `Mapped[...]`, Pydantic v2 schemas, Alembic) é
> responsabilidade da fase de implementação e não é fixada aqui.

---

## Visão geral

O modelo é composto por **cinco entidades** que refletem o fluxo do
produto: um usuário autenticado, projetos (agrupamento humano),
arquivos de modelo (recurso físico carregado), jobs de conversão
(unidade de processamento assíncrono) e links de compartilhamento
(token público para o cliente final).

```
User ───< Project ───< ModelFile ───< ConversionJob
                                       │
                                       │
User ───< ShareLink >──── Project
```

Relacionamentos em texto:
- Um `User` possui zero ou mais `Project`.
- Um `Project` possui um ou mais `ModelFile` (re-uploads são permitidos;
  cada `ModelFile` representa uma versão física carregada).
- Cada `ModelFile` está associado a um `ConversionJob` (relação 1:1 —
  um arquivo gera no máximo um job por vez; re-uploads criam novos
  jobs para o mesmo `Project`).
- Um `Project` possui zero ou mais `ShareLink`. Um `ShareLink` aponta
  para o `ModelFile` que está sendo compartilhado (não para o
  `Project` inteiro) — assim o owner pode compartilhar uma versão
  específica.

---

## Entidades

### User

Representa uma conta autenticada (profissional que faz upload).

| Atributo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | UUID | PK, gerado no servidor | Identificador estável. |
| `email` | string | único, normalizado (lower) | Login. |
| `password_hash` | string | não-nulo, opaco (bcrypt/argon2) | Hash da senha. Senha nunca armazenada. |
| `display_name` | string | opcional | Nome exibido no UI. |
| `created_at` | timestamp | imutável | Instante de criação. |
| `updated_at` | timestamp | atualizado em qualquer mutação | Última modificação. |
| `is_active` | bool | default `true` | Desativação manual. |

**Validações**:
- `email` deve ser sintaticamente válido.
- `password` no momento do registro: ≥ 8 caracteres, não-comprável a
  email, hash obrigatório antes de persistir.
- `password_hash` nunca é exposto em responses.

### Project

Representa um projeto do usuário — agrupamento humano de um ou mais
modelos carregados.

| Atributo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | UUID | PK | Identificador estável. |
| `owner_id` | UUID | FK → `User.id`, não-nulo | Dono. |
| `name` | string | 1–120 chars, não-vazio | Nome humano. |
| `description` | text | opcional | Descrição livre. |
| `created_at` | timestamp | imutável | Instante de criação. |
| `updated_at` | timestamp | atualizado em qualquer mutação | Última modificação. |
| `archived_at` | timestamp | nullable | Soft-delete (projetos arquivados não aparecem em listagens padrão). |

**Validações**:
- Apenas o `owner` pode ler/mutar/excluir o `Project`.
- `name` trimmed; `""` rejeitado.
- Re-uploads não alteram `name` (a versão é controlada via
  `ModelFile`).

### ModelFile

Representa o arquivo de modelo carregado dentro de um `Project`.

| Atributo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | UUID | PK | Identificador estável. |
| `project_id` | UUID | FK → `Project.id`, não-nulo | Projeto dono. |
| `uploader_id` | UUID | FK → `User.id`, não-nulo | Quem subiu. |
| `original_filename` | string | ≤ 255 chars, sanitizado | Nome do arquivo original. |
| `source_format` | enum | não-nulo | `ifc` \| `dae` \| `obj` \| `glb`. |
| `size_bytes` | int64 | > 0, ≤ limite do MVP | Tamanho. |
| `original_storage_key` | string | path abstrato, não-nulo | Chave para `ObjectStorage` (resolve para `storage/originals/<project_id>/<file_id>__<sanitized_name>`). |
| `uploaded_at` | timestamp | imutável | Instante do upload. |
| `content_hash` | string (hex) | SHA-256, 64 chars | Integridade. |

**Validações**:
- `source_format` deve estar entre os suportados pelo MVP
  (`ifc`, `dae`, `obj`, `glb`). `stl`, `rvt`, `dwg`, `dxf`, `skp`
  são **fora do MVP** e devem ser rejeitados com HTTP 415.
- `size_bytes` ≤ `MAX_UPLOAD_MB * 1024 * 1024` (limite do MVP).
- `content_hash` calculado no upload e revalidado quando o worker
  lê o arquivo (defesa contra corrupção de storage).
- Magic bytes do arquivo devem bater com `source_format` declarado
  (ex.: IFC começa com `ISO-10303-21`; DAE é XML com `COLLADA`;
  GLB começa com `glTF` magic; OBJ começa com `#` ou `v`).

### ConversionJob

Representa a unidade de trabalho assíncrono: a conversão do
`ModelFile` em GLB + thumbnail.

| Atributo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | UUID | PK | Identificador estável. |
| `model_file_id` | UUID | FK → `ModelFile.id`, único, não-nulo | Arquivo de origem. |
| `status` | enum | não-nulo | `pending` \| `running` \| `ready` \| `failed`. |
| `attempts` | int | default `0` | Contagem de tentativas de execução. |
| `last_error` | text | opcional, populado em `failed` | Mensagem de erro do worker. |
| `started_at` | timestamp | nullable | Quando o worker pegou a task. |
| `finished_at` | timestamp | nullable | Quando terminou (com sucesso ou falha). |
| `created_at` | timestamp | imutável | Quando a entidade foi criada (= quando o upload foi aceito). |
| `glb_storage_key` | string | nullable, populado em `ready` | Chave do GLB produzido. |
| `thumbnail_storage_key` | string | nullable, populado em `ready` | Chave do thumbnail WebP. |
| `duration_ms` | int | nullable, populado em `ready`/`failed` | Tempo total de execução. |

**Máquina de estados**:

```
                ┌────────┐
                │pending │   ← estado inicial, logo após aceitação do upload
                └───┬────┘
                    │  worker pega a task
                    ▼
                ┌────────┐
                │running │
                └────┬───┘
       ┌────────────┴────────────┐
       ▼ sucesso                  ▼ falha
   ┌────────┐                  ┌────────┐
   │ ready  │                  │ failed │
   └────────┘                  └────────┘
       (terminal)               (terminal, mas retentável manualmente
                                 via endpoint explícito)
```

**Validações**:
- Transições só na direção `pending → running → {ready, failed}`.
- Re-encoding de um `ModelFile` existente (re-upload ou retry manual)
  cria **um novo** `ConversionJob` (imutabilidade histórica).
- `attempts` ≤ limite configurado (evitar loop infinito em erros
  determinísticos).

### ShareLink

Representa o link público de visualização que o owner envia ao
cliente.

| Atributo | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | UUID | PK | Identificador estável. |
| `token` | string | único, ≥ 128 bits de entropia | Token opaco da URL pública. |
| `project_id` | UUID | FK → `Project.id`, não-nulo | Projeto dono. |
| `model_file_id` | UUID | FK → `ModelFile.id`, não-nulo | Versão específica do modelo compartilhado. |
| `created_by` | UUID | FK → `User.id`, não-nulo | Quem gerou. |
| `created_at` | timestamp | imutável | Instante de criação. |
| `revoked_at` | timestamp | nullable | Soft-revogação. |

**Validações**:
- `token` gerado server-side com CSPRNG; nunca exposto em logs.
- `revoked_at IS NOT NULL` bloqueia o acesso público.
- Acesso público é `GET /share/{token}` — não exige auth; o token
  é a credencial.

> **Fora do MVP** (registrado para clareza):
> - `expires_at` — share link não expira. Adicionar quando for
>   requisito explícito.
> - `view_count` — telemetria de visualização. Adicionar quando
>   houver requisito de analytics.

---

## Cardinalidades (resumo)

| Origem | → | Destino | Cardinalidade | Notas |
|---|---|---|---|---|
| `User` | → | `Project` | 1:N | `Project.owner_id` |
| `Project` | → | `ModelFile` | 1:N | `ModelFile.project_id` |
| `User` | → | `ModelFile` | 1:N | `ModelFile.uploader_id` (uploader pode ser ≠ owner se houver colaboração futura; no MVP, sempre igual ao owner) |
| `ModelFile` | → | `ConversionJob` | 1:1 (histórico) | Cada arquivo pode ter múltiplos jobs ao longo do tempo (reattempts), mas apenas o `latest ready` é considerado o "atual" |
| `Project` | → | `ShareLink` | 1:N | Múltiplos links simultâneos permitidos |
| `ShareLink` | → | `ModelFile` | N:1 | Um link aponta para **uma** versão do modelo |
| `ShareLink` | → | `User` | N:1 (criador) | Auditoria |

---

## Invariantes

1. **Um `ModelFile` é imutável após o upload.** Reprocessamento não
   substitui o arquivo; cria um novo job.
2. **Apenas o `owner` do `Project` pode mutar o projeto e seus
   descendentes** (`ModelFile`, `ConversionJob`, `ShareLink`).
3. **`ConversionJob.glb_storage_key` e `thumbnail_storage_key`
   populados ⇔ `status == ready`**. Em `failed`, ambos são `null`.
4. **`ShareLink` é inválido quando `revoked_at IS NOT NULL`.**
5. **`ConversionJob` aceita reentrega** (atualização atômica de
   `status`) — não há duas transições concorrentes; o worker faz
   `SELECT ... FOR UPDATE` ou update condicional.

---

## Estados derivados (não-persistidos)

- **`Project.latest_model_file`**: o `ModelFile` com `uploaded_at`
  mais recente.
- **`Project.latest_ready_job`**: o `ConversionJob` mais recente com
  `status == ready` (se houver).
- **`Project.is_viewable`**: `latest_ready_job IS NOT NULL`.

Esses valores não são colunas — são derivados em queries.

---

## Modelo de arquivos (filesystem)

Layout canônico, servido via abstração `ObjectStorage`:

```
storage/
  originals/
    <project_id>/
      <model_file_id>__<sanitized_original_name>
  converted/
    <project_id>/
      <model_file_id>.glb
  thumbnails/
    <project_id>/
      <model_file_id>.webp
```

Cada `ModelFile` tem um diretório dedicado dentro de
`<project_id>/` para que a remoção de um projeto (ou de uma versão)
seja uma operação atômica de remoção de pasta.

---

## Escopo do MVP (reafirmação)

Estes **não** são modelados no MVP:
- Permissões granulares (roles, ACL)
- Comentários
- Versionamento explícito (entidade `Version` separada; o
  `ModelFile` carrega seu próprio histórico por timestamp)
- BIM tree / propriedades IFC
- Digital twin / telemetria de visualização
- Auditoria detalhada (apenas `created_at`/`updated_at`)

Esses itens não constam no modelo conceitual. Adicioná-los
posteriormente **exige** revisão da Constituição.
