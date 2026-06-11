<!--
  Sync Impact Report:
  ==================
  Version change: 1.1.0 → 2.0.0 (MAJOR: complete stack redefinition —
  Python/FastAPI backend replaces ASP.NET Core; project repositioned
  from "BIM" to general 3D viewer; vertical-slice feature layout;
  async processing, local-disk storage, GLB-centric pipeline)

  Modified principles:
  - I. Clean Code & MVP Pragmatism → 1. Simplicidade
  - II. Meaningful Naming & Structure → absorbed into 1, 2, 5
  - III. Small Units & Single Responsibility → absorbed into 1
  - IV. Tests Mirror Structure (Backend/Frontend Separation) → 2. Vertical Slice + 9. Testabilidade
  - V. Self-Documenting Code & Minimal Comments → absorbed into 1, 10
  - Route Boundary: Admin vs. Public Share → removed (replaced by
    general 6. Visualização guidance; no admin/public route split
    codified in this version)

  Added sections:
  - Project name: App 3D Viewer (replaces Arch3DAR framing)
  - Objective: explicit non-BIM positioning; non-goals stated
  - 2. Vertical Slice — features/ layout as the canonical structure
  - 3. Backend Python (FastAPI, Pydantic v2, SQLAlchemy 2, Alembic,
    PostgreSQL; full typing)
  - 4. Conversão de Arquivos — Blender Headless, IfcOpenShell, Trimesh,
    Open3D, pygltflib; materials/textures/UVs over BIM metadata
  - 5. Frontend — React + TypeScript + Vite + TanStack Query +
    React Router; strict TS, no plain JS
  - 6. Visualização — GLB as canonical internal format; model-viewer
    and Three.js preferred
  - 7. Armazenamento — local disk for MVP; no MinIO/S3; abstraction
    for future migration
  - 8. Processamento Assíncrono — Celery + Redis (or equivalent);
    no blocking HTTP conversions
  - 9. Testabilidade — every feature requires unit tests and
    integration tests when applicable; nothing done without tests
  - 10. Proibição de Assunções — never invent requirements; STOP
    and ask when unclear
  - 11. Critério de Conclusão — code + tests + executed + validated
  - 12. MVP — explicit in-scope set; anything else is future work

  Removed sections:
  - "Route Boundary: Admin vs. Public Share" (no longer applicable
    to the new product framing; can be re-added in a future amendment
    if a public-share route is reintroduced)
  - References to ASP.NET Core, dotnet format, IFC/BIM framing
  - `app/tests/{backend,frontend}/` mirrored test layout (replaced
    by feature-local `tests/` in the vertical-slice structure)

  Templates requiring updates:
  - .specify/templates/plan-template.md (⚠ pending — references to
    backend/frontend separation and "Constitution Check" wording
    should be reviewed against the new principles)
  - .specify/templates/spec-template.md (⚠ pending — review scope
    and requirements alignment with the new MVP scope statement)
  - .specify/templates/tasks-template.md (⚠ pending — task paths
    should reflect the new features/ layout)
  - .specify/templates/checklist-template.md (✅ generic, no change)
  - .specify/templates/constitution-template.md (✅ not user-facing,
    template preserved)
  - README.md / docs/quickstart.md (⚠ pending — references to
    ASP.NET Core, IFC/BIM framing, and the previous structure need
    to be updated; OUT OF SCOPE for this amendment per user
    instruction to modify only the constitution)

  Follow-up TODOs:
  - TODO(CONSTITUTION_MIGRATION): The current implementation under
    `app/backend/` is ASP.NET Core 9 (C#) and the active plan/scope
    in `specs/001-ifc-mvp-platform/` still references the IFC MVP
    framing. This constitution declares the target stack; an
    explicit migration plan is required before code is rewritten
    in Python/FastAPI. Do not silently rewrite production code as
    a side effect of this amendment.
  - TODO(STORAGE_ABSTRACTION): The local-disk storage rule requires
    a storage interface so that future migration to object storage
    is feasible without rewriting call sites.
-->

# App 3D Viewer Constitution

## Nome

App 3D Viewer

## Objetivo

O App 3D Viewer é uma plataforma web para compartilhamento e visualização
de modelos 3D.

O usuário realiza upload de arquivos de modelagem 3D, o sistema converte para
GLB quando necessário e gera um link público para visualização em navegador e
Realidade Aumentada.

O foco principal é arquitetura, interiores, móveis planejados e apresentação
comercial de projetos.

O sistema **NÃO** é um software BIM.

O sistema **NÃO** tem como objetivo competir com Revit, Navisworks ou
Solibri.

O objetivo é visualização e compartilhamento simples.

---

# PRINCÍPIOS FUNDAMENTAIS

## 1. Simplicidade

Sempre escolher a solução mais simples que atenda o requisito.

Evitar:

- DDD complexo
- CQRS desnecessário
- Event Sourcing
- Arquiteturas excessivamente sofisticadas
- Camadas redundantes

**Rationale**: Complexidade só se justifica quando o requisito atual
exige. MVP não comporta abstrações especulativas.

## 2. Vertical Slice

A organização do backend deve ser por funcionalidade.

Estrutura preferencial:

```
features/
    upload_model/
    convert_model/
    generate_thumbnail/
    share_model/
    projects/
    authentication/
```

Cada feature deve conter seus próprios:

- endpoints
- schemas
- services
- tests

Evitar pastas globais de `services/` e `repositories/` quando possível.

**Rationale**: Agrupar por feature mantém acoplamento e coesão
próximos; reduz o custo cognitivo de localizar uma responsabilidade
e torna o descarte de uma feature atômico.

## 3. Backend Python

O backend utiliza:

- **FastAPI**
- **Pydantic v2**
- **SQLAlchemy 2**
- **Alembic**
- **PostgreSQL**

Todo código deve ser totalmente tipado.

Toda função pública deve possuir type hints.

**Rationale**: Stack homogênea, com validação em borda (Pydantic) e
migrações versionadas (Alembic) alinhadas ao princípio de simplicidade.

## 4. Conversão de Arquivos

A conversão é uma capacidade central do produto.

Devem ser priorizadas bibliotecas Python para processamento 3D.

Tecnologias preferenciais:

- **Blender Headless**
- **IfcOpenShell**
- **Trimesh**
- **Open3D**
- **pygltflib**

Sempre priorizar preservação de:

- materiais
- texturas
- UV mapping

sobre metadados BIM.

**Rationale**: O produto vende apresentação visual, não interoperabilidade
BIM. Materiais e texturas corretos são o que o usuário percebe; metadados
BIM são dispensáveis fora do nicho AEC pesado.

## 5. Frontend

Stack oficial:

- **React**
- **TypeScript**
- **Vite**
- **TanStack Query**
- **React Router**

Todo código frontend deve ser TypeScript estrito.

Não utilizar JavaScript puro.

**Rationale**: Type safety na borda do cliente elimina classes inteiras de
bugs e mantém contratos com a API explícitos.

## 6. Visualização

Formato interno padrão:

- **GLB**

Todo fluxo do sistema deve convergir para GLB.

Visualização preferencial:

- **`<model-viewer>`** (Google)
- **Three.js** quando necessário

**Rationale**: GLB é binário, único arquivo, amplamente suportado por
`<model-viewer>` e pela Web. Centralizar no GLB simplifica o pipeline
de cache, CDN e viewer.

## 7. Armazenamento

Durante o MVP:

- armazenamento **local em disco**.

Não utilizar MinIO.

Não utilizar S3.

A abstração de storage deve permitir futura migração.

**Rationale**: Para um MVP, o custo de operar um object store excede o
ganho. A obrigatoriedade de uma abstração evita que o "MVP local" vire
uma reescrita quando o tráfego justificar object storage.

## 8. Processamento Assíncrono

Conversões **não devem bloquear** requisições HTTP.

Utilizar fila de processamento.

Tecnologias preferenciais:

- **Celery + Redis**

ou equivalente simples.

**Rationale**: Conversão 3D é cara em CPU e tempo. Bloquear a request
HTTP degrada UX e acopla o front a limites do worker. Uma fila desacopla
aceitação de processamento e permite retries e backpressure naturais.

## 9. Testabilidade

Toda feature deve possuir:

- testes unitários
- testes de integração quando aplicável

**Não marcar tarefas como concluídas sem testes.**

**Rationale**: Sem testes, a stack de conversão 3D — que depende de
Blender, IFC, geometria — regride silenciosamente a cada mudança. Testes
são a especificação executável do comportamento.

## 10. Proibição de Assunções

- Nunca inventar requisitos.
- Nunca criar funcionalidades não especificadas.
- Nunca inferir regras de negócio não documentadas.

Quando houver dúvida: **PARAR** e solicitar esclarecimento.

**Rationale**: Um agente que infere requisitos pode introduzir um
produto diferente do que o usuário pediu. Em MVP, escopo não-declarado
é dívida imediata.

## 11. Critério de Conclusão

Uma tarefa somente pode ser considerada concluída quando **todos** os
itens abaixo forem satisfeitos:

- código implementado
- testes implementados
- testes executados
- resultado validado

A ausência de qualquer item **impede** marcar como concluído.

**Rationale**: "Terminei" sem testes executados é uma asserção sem
evidência. Em um pipeline de conversão 3D, "compilou" não significa
"funciona" — geometria, materiais e UVs só se provam com testes
executados.

## 12. MVP

Escopo inicial:

- upload de modelos
- conversão para GLB
- geração de thumbnail
- geração de link público
- visualização 3D
- visualização AR

Qualquer funcionalidade fora desse escopo deve ser tratada como futura
expansão.

**Rationale**: Escopo explícito protege o time da tentação de
"já que estou aqui, faço também…". Cada item fora do MVP é uma
decisão de roadmap, não uma decisão de implementação.

---

## Governance

Esta Constituição é o documento soberano para todas as decisões de
arquitetura, stack, estrutura de código e prática de desenvolvimento do
projeto. Ela se sobrepõe a hábitos informais e preferências pessoais.

### Amendment Procedure

1. Propor mudança em `.specify/memory/constitution.md` via Pull Request.
2. Documentar rationale, impacto no código existente e caminho de
   migração (se aplicável).
3. Ao menos uma aprovação é necessária.
4. Atualizar `LAST_AMENDED_DATE` e incrementar `CONSTITUTION_VERSION`
   conforme a política de versionamento abaixo.

### Versioning Policy

- **MAJOR** (x.0.0): remoções ou redefinições incompatíveis de
  princípios; mudanças de stack; reescopo de produto.
- **MINOR** (0.x.0): novo princípio adicionado; orientação
  materialmente expandida.
- **PATCH** (0.0.x): clarificações, correções de wording,
  refinamentos não-semânticos.

### Compliance Review

Toda execução de `/speckit-plan` deve incluir uma etapa de Constitution
Check. Violações devem ser documentadas na seção de Complexity Tracking
do plano. Violações persistentes ou severas podem bloquear a
implementação até resolução.

---

**Version**: 2.0.0 | **Ratified**: 2026-06-09 | **Last Amended**: 2026-06-11

### 2.0.0 Amendment Notes

- Reposicionamento do produto: de "Arch3DAR — IFC/BIM MVP" para
  **App 3D Viewer** — visualização e compartilhamento 3D genérico,
  sem pretensão de ser software BIM.
- Stack do backend **migrada de ASP.NET Core 9 (C#) para Python**
  (FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + PostgreSQL).
- Frontend mantido (React + TypeScript), com stack explicitada:
  Vite + TanStack Query + React Router.
- Estrutura de código backend migrada de separação
  `controllers/services/repositories/` para **vertical slice por
  feature** (`features/upload_model/`, `features/convert_model/`,
  …).
- Conversão 3D declarada como **capacidade central**, com stack
  preferencial: Blender Headless, IfcOpenShell, Trimesh, Open3D,
  pygltflib. Preservação de materiais/texturas/UVs sobre metadados BIM.
- Formato interno canônico: **GLB**. Viewer preferencial: `<model-viewer>`,
  com Three.js como alternativa.
- Armazenamento MVP: **disco local**, com abstração obrigatória para
  permitir futura migração para object storage. Proibição explícita
  de MinIO/S3 neste momento.
- Conversões são **assíncronas** via Celery + Redis (ou equivalente).
- Adicionados princípios explícitos: **Proibição de Assunções** e
  **Critério de Conclusão** (código + testes + execução + validação).
- **MVP** explicitado em lista fechada; qualquer item fora dela é
  expansão futura.
- Removida a seção "Route Boundary: Admin vs. Public Share" —
  aplicável ao framing anterior; pode ser reintroduzida por amendment
  futuro se a rota pública de share voltar a ser um recorte relevante.
- **Atenção**: o código atual do repositório (`app/backend/` em
  ASP.NET Core 9) e o escopo ativo em `specs/001-ifc-mvp-platform/`
  ainda refletem a versão 1.x desta constituição. A 2.0.0 declara o
  **alvo arquitetural**; uma migração de código deve ser planejada
  antes de qualquer reescrita — não é efeito colateral desta alteração.
