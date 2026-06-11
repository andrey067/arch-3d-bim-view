# Research — App 3D Viewer (MVP)

**Feature**: `001-ifc-mvp-platform` (App 3D Viewer MVP)
**Stack alvo**: Python/FastAPI + React/TypeScript + PostgreSQL + Redis/Celery + GLB
**Status da Constituição**: v2.0.0 (aprovada em 2026-06-09, alterada em 2026-06-11)

Este artefato registra as decisões técnicas e os fundamentos que sustentam o
plano. Onde a Constituição já declara a escolha (stack, vertical slice,
GLB, abstração de storage, Celery, etc.), a pesquisa valida a coerência da
combinação. Onde havia ambiguidade de implementação, ela foi resolvida
abaixo. Não há alternativas em aberto: a stack está congelada por
instrução do usuário e pela Constituição.

---

## R-1 — Stack: backend Python (FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic)

- **Decision**: FastAPI como framework HTTP; Pydantic v2 para validação e
  schemas; SQLAlchemy 2 (estilo 2.0, com `Mapped`/`mapped_column`) para
  ORM; Alembic para migrações; PostgreSQL como banco.
- **Rationale**: Homogeneidade da stack Python elimina a fricção de
  manter dois runtimes e dois conjuntos de dependências. FastAPI dá
  OpenAPI gerado automaticamente, validação de borda via Pydantic, e
  async nativo. SQLAlchemy 2 + Alembic é a combinação canônica para
  migrações versionadas e type hints modernos. PostgreSQL cobre JSON
  para metadados, índices GIN, e tipos `uuid`/`text`/`bytea` que o
  pipeline de conversão exige.
- **Alternatives considered**: Django (rejeitado por ceremony/ORM
  opinativo que conflita com vertical slice); Flask (rejeitado por não
  ter validação/typing de borda); NestJS/Express em Node (rejeitado
  pela instrução do usuário e Constituição).

## R-2 — Frontend: React + TypeScript estrito + Vite + TanStack Query + React Router

- **Decision**: React 18+, TypeScript estrito, Vite como build tool,
  TanStack Query para cache de servidor, React Router para navegação.
- **Rationale**: TypeScript estrito na borda do cliente elimina classes
  inteiras de bugs e mantém o contrato com a API explícito. Vite dá HMR
  rápido e build de produção enxuto. TanStack Query cobre
  fetch/cache/retry/refetch sem reinventar a roda; encaixa
  naturalmente em fluxos assíncronos (status de conversão). React
  Router é a solução canônica de roteamento client-side.
- **Alternatives considered**: Next.js (rejeitado por SSR/SSG/RSC que o
  MVP não precisa e que adicionam deploy complexity); Remix (mesmo
  motivo); SWR (rejeitado por ter menos features que TanStack Query
  out-of-the-box, sem benefício claro).

## R-3 — Banco: PostgreSQL

- **Decision**: PostgreSQL como único datastore relacional.
- **Rationale**: Tipos ricos (`uuid`, `text`, `jsonb`, `bytea`), índices
  GIN/GIST quando necessário, transações ACID para garantir consistência
  do estado de `ConversionJob` (Pending → Running → Ready/Failed).
  Postgres é o banco da stack.
- **Alternatives considered**: SQLite (rejeitado para o MVP em ambiente
  com worker assíncrono — risco de locking sob concorrência). MySQL
  (rejeitado por preferência explícita da Constituição).

## R-4 — Cache e Filas: Redis + Celery

- **Decision**: Redis como broker e result backend do Celery.
- **Rationale**: Celery é o padrão de fato em Python para filas com
  retry, backoff, e visibilidade operacional. Redis como broker dá
  latência baixa e simplicidade operacional no MVP. Result backend em
  Redis permite consultar estado do job sem reabrir a fila.
- **Alternatives considered**: RQ (rejeitado por ter menos features de
  orquestração); Dramatiq (rejeitado por ser menos convencional);
  RabbitMQ (rejeitado por ser mais complexo de operar no MVP);
  Postgres-as-queue (rejeitado por anti-padrão de polling no banco).

## R-5 — Conversão: Blender Headless + IfcOpenShell

- **Decision**: Apenas duas tecnologias de conversão no MVP:
  - **Blender Headless**: import de DAE/OBJ, export GLB com
    materiais/UVs preservados, e render de thumbnail WebP.
  - **IfcOpenShell**: extração de geometria de IFC.
- **Rationale**: O Blender é uma **caixa única** para (1) importar
  DAE/OBJ, (2) exportar GLB válido, e (3) renderizar thumbnails
  com câmera automática. O IfcOpenShell é a única lib Python
  madura para extrair geometria de IFC. **Não há requisito
  concreto** de decimação, simplificação, LOD, ou manipulação
  avançada de malha no MVP — então Trimesh, Open3D e pygltflib
  ficam fora até que um FR concreto apareça.
- **Trimesh / Open3D / pygltflib**: **explicitamente fora do MVP**.
  Reintroduzir **apenas** quando houver requisito concreto de
  manipulação de malha (decimação, simplificação, LOD) ou
  validação/inspeção programática de GLB. Justificativa para
  manter fora agora:
  - **Open3D**: sem FR de decimação/simplificação. Acrescenta
    ~200 MB na imagem Docker sem benefício.
  - **pygltflib**: Blender já produz GLB válido. Validação extra
    é redundância.
  - **Trimesh**: Blender + IfcOpenShell cobrem a normalização
    necessária no MVP. Reintroduzir se aparecer requisito de
    mesh repair, limpeza, ou decimação.
- **Alternatives considered**: assimp (rejeitado por ser C++ e ter
  bindings menos estáveis que o stack Python preferido);
  Trimesh/Open3D/pygltflib (rejeitados por ausência de FR).

## R-6 — Formato interno canônico: GLB

- **Decision**: Todo fluxo converge para GLB. Não há suporte a múltiplos
  formatos internos. Visualização web e AR (Android/iOS) consomem o
  GLB.
- **Rationale**: GLB é binário, arquivo único, amplamente suportado
  por `<model-viewer>`, Three.js, e plataformas de AR (Scene Viewer
  Android + Quick Look iOS via USDZ derivado do GLB). Centralizar no
  GLB simplifica o pipeline de cache, a superfície de teste e a
  entrega ao cliente.
- **Alternatives considered**: USDZ primário (rejeitado porque USDZ tem
  suporte web limitado; o pipeline precisa de GLB para `<model-viewer>`
  no navegador). glTF + bin/texturas separados (rejeitado por fricção
  de servir múltiplos arquivos e CORS).

## R-7 — Visualização: `<model-viewer>` (Google)

- **Decision**: `<model-viewer>` é a primitiva de visualização padrão
  no frontend. AR para Android via Scene Viewer; AR para iOS via
  Quick Look (USDZ derivado do GLB).
- **Rationale**: `<model-viewer>` já implementa orbit/zoom/auto-rotate,
  poster, fallback gracioso para ambientes sem WebGL, e tem atributo
  `ar`/`ar-modes` para acionar AR nativo. Three.js pode ser usado
  pontualmente quando algum controle específico não é exposto por
  `<model-viewer>`.
- **Alternatives considered**: Babylon.js (rejeitado por ter ecossistema
  mais pesado e sem ganho claro). Three.js puro para tudo (rejeitado
  por reescrever controles que `<model-viewer>` já dá pronto).

## R-8 — Armazenamento: disco local com abstração

- **Decision**: Storage MVP em disco local, com interface
  `ObjectStorage` (Python) que abstrai `put`, `get`, `delete`,
  `presigned_url` (quando aplicável), `exists`. A primeira
  implementação é `LocalDiskStorage` servindo de `storage/originals/`,
  `storage/converted/`, `storage/thumbnails/`.
- **Rationale**: O custo de operar MinIO/S3 no MVP excede o ganho. A
  abstração obrigatória impede que a troca futura vire reescrita. As
  três pastas canônicas (`originals/`, `converted/`, `thumbnails/`)
  isolam o ciclo de vida de cada artefato.
- **Alternatives considered**: MinIO/S3 (rejeitados pela Constituição).
  Banco `bytea` (rejeitado por tornar o banco caminho crítico para
  servir arquivos estáticos grandes).

## R-9 — Autenticação própria: JWT Access + Refresh

- **Decision**: Implementação própria de autenticação com par de tokens
  (Access de curta duração + Refresh de longa duração). Sem provedores
  externos.
- **Rationale**: A Constituição proíbe Clerk/Auth0/Firebase Auth. JWT
  próprio é simples, suficiente para o MVP, e mantém dependências sob
  controle. Access token carrega `user_id`, expiração curta (ex.
  15 min). Refresh token é opaco, armazenado com hash, com rotação.
- **Alternatives considered**: Sessão server-side (rejeitada por
  adicionar estado ao backend sem ganho claro em MVP). OAuth externo
  (rejeitado pela proibição). Token único sem refresh (rejeitado por
  UX pior em mobile).

## R-10 — Processamento assíncrono (Celery) e contrato Upload → Job → Worker

- **Decision**: Conversões executam em worker Celery. Endpoint HTTP de
  upload persiste o original, cria `ConversionJob` em estado
  `pending`, enfileira a task e responde `202 Accepted` com ID do job
  para o frontend pollar/observar. Worker atualiza o job para
  `running`, depois `ready` ou `failed`, com paths dos artefatos.
- **Rationale**: Conversão 3D consome CPU e tempo variáveis; bloquear
  a request HTTP degradaria UX e amarraria o front aos limites do
  worker. Fila desacopla aceitação de processamento, dá retry/backoff
  naturais e observabilidade operacional.
- **Alternatives considered**: Background tasks do FastAPI
  (`BackgroundTasks` — rejeitado por morrer com o processo, sem
  persistência de fila). Execução síncrona (rejeitada pelo princípio
  de não bloquear HTTP).

## R-11 — Vertical Slice (organização por feature)

- **Decision**: Backend organizado em `apps/backend/app/features/<feature>/`
  contendo `router`, `schemas`, `service`, `persistence`, `tests`. Sem
  `repositories/` global, sem `services/` global, sem `domain/` global.
  O mínimo de camadas compartilhadas vive em `core/` (config, db,
  storage, security).
- **Rationale**: A Constituição v2.0.0 codifica vertical slice como
  princípio. Coesão de feature reduz custo cognitivo e torna descarte
  de feature atômico. Camadas globais virariam god-folders.
- **Alternatives considered**: Camadas clássicas (rejeitado pela
  Constituição). Hexagonal/Clean (rejeitado por ser overkill para
  MVP).

## R-12 — Monorepo: `apps/`, `infra/`, `docs/`, `storage/`

- **Decision**: Repositório único com diretórios canônicos:
  - `apps/frontend/` — SPA React
  - `apps/backend/` — API FastAPI
  - `apps/converter/` — opcional (worker/Blender/IfcOpenShell) — fica
    dentro do worker Celery ou em imagem dedicada; **decidido**:
    dentro do `apps/backend` como módulo de worker
    (`apps/backend/app/conversion/`) e imagem Docker dedicada em
    `infra/docker/`. Justificativa: simplifica deploy (uma imagem com
    deps pesadas) e mantém o princípio 1 (simplicidade).
  - `infra/docker/` — Dockerfiles e Compose
  - `docs/` — documentação não-específica-de-feature
  - `storage/` — mount de volume para `originals/`, `converted/`,
    `thumbnails/`
- **Rationale**: O usuário definiu o layout. O worker de conversão
  precisa de Blender + IfcOpenShell (apenas essas duas libs no
  MVP — Trimesh/Open3D/pygltflib foram explicitamente removidos);
  empacotar isso em uma imagem dedicada do backend evita deploy
  de dois runtimes Python separados para uma única fila.
- **Alternatives considered**: `apps/converter/` como pacote separado
  (rejeitado por adicionar segunda imagem e segundo entrypoint para
  uma única fila). Manter como sidecar HTTP separado (rejeitado por
  adicionar latência de rede e mais um serviço para operar).

## R-13 — Entidades do modelo conceitual

- **Decision**: `User`, `Project`, `ModelFile`, `ConversionJob`,
  `ShareLink`. Sem `Version`, sem `Comment`, sem `Permission` no MVP.
- **Rationale**: Cada entidade representa uma responsabilidade clara
  dentro do escopo de MVP. O modelo é deliberadamente magro: o objetivo
  é suportar o fluxo `Upload → Process → Share → View → AR`.
- **Alternatives considered**: Incorporar tudo em `Project` (rejeitado
  por misturar o conceito de "projeto" — agrupamento humano — com
  "arquivo de modelo" — recurso físico, e "job" — unidade de
  processamento). Adicionar versionamento (rejeitado por estar fora
  do MVP).

## R-14 — Pipeline de conversão: convergência para GLB

- **Decision**: O pipeline de worker, independentemente do formato de
  entrada, produz três artefatos canônicos no diretório do `Project`:
  - `<project_id>/originals/<source>` — original preservado
  - `<project_id>/converted/model.glb` — GLB canônico
  - `<project_id>/thumbnails/thumbnail.webp` — preview
- **Rationale**: A convergência para GLB é o que permite que o
  restante do sistema (frontend, AR) tenha um único caminho de
  leitura. Preservar o original é importante para reprocessamento
  futuro.
- **Alternatives considered**: Descartar o original após conversão
  (rejeitado por perder capacidade de reprocessar com versões
  futuras do pipeline). Múltiplos formatos internos (rejeitado por
  противоречит a Constituição).

## R-15 — Estratégia de processamento (matriz formato × tecnologia)

- **Decision (matriz)**:
  - **IFC** → IfcOpenShell extrai geometria (com materiais/UVs
    preservados) → exporta como malha intermediária ou .obj/.gltf
    interno → Blender headless importa → exporta GLB canônico →
    thumbnail WebP. **(STL, Trimesh, Open3D, pygltflib ficam
    fora do MVP.)**
  - **DAE / OBJ** → Blender headless importa → exporta GLB (com
    materiais/UVs) → thumbnail WebP.
  - **GLB de entrada** → Blender headless normaliza (eixos,
    escala) e gera thumbnail; o GLB é o próprio canônico
    (operação é idempotente).
  - **STL** → **fora do MVP**. STL é mesh pura, sem materiais
    nem texturas, e não atende o objetivo do produto
    (arquitetura, interiores, móveis planejados). Rejeitar
    com HTTP 415 e mensagem clara.
  - **RVT/DWG/DXF** → fora do MVP (sem conversor open-source
    confiável). Devem ser tratados como "não suportado no MVP" e
    rejeitados com mensagem clara.
  - **SKP** → fora do MVP (sem licença livre do formato). Rejeitar
    com mensagem clara.
- **Rationale**: Cada formato tem um caminho de extração mais
  confiável. IFC tem o IfcOpenShell maduro; DAE/OBJ são cobertos
  nativamente pelo Blender; GLB entrada é o caso trivial de
  re-empacotar.
- **Alternatives considered**: Um único conversor para todos
  (rejeitado por não preservar materiais/UVs em IFC sem IfcOpenShell).
  Pipeline "via Blender para tudo" (rejeitado por overhead de subir
  Blender para cada job — IfcOpenShell é mais leve para IFC).
  Trimesh/Open3D/pygltflib (rejeitados por ausência de FR no MVP).

## R-16 — Estratégia de armazenamento (filesystem)

- **Decision**: Layout físico:
  ```
  storage/
    originals/<project_id>/<source_filename>
    converted/<project_id>/model.glb
    thumbnails/<project_id>/thumbnail.webp
  ```
  Acesso via `apps/backend/app/core/storage/LocalDiskStorage.py`,
  registrado na injeção de dependência como implementação de
  `ObjectStorage`.
- **Rationale**: Diretório por `project_id` isola o ciclo de vida
  (exclusão de um projeto = remoção de uma pasta). Três árvores
  canônicas separam originais (preservados), convertidos
  (reprocessáveis), e thumbnails (derivados baratos).
- **Alternatives considered**: Um único diretório plano (rejeitado
  por não permitir ciclo de vida por projeto). Path único por
  arquivo (rejeitado por perder agrupamento semântico).

## R-17 — Auth: hashing de senha e rotação de refresh

- **Decision**: Hashing com bcrypt (passlib) ou argon2id. Refresh token
  armazenado **como hash** (não em texto puro). Rotação obrigatória
  de refresh token a cada uso.
- **Rationale**: Boas práticas mínimas de segurança para MVP.
  Refresh opaco + hash impede que vazamento do banco exponha
  tokens válidos.
- **Alternatives considered**: SHA-256 (rejeitado por não ter salt
  por padrão e ser rápido demais contra brute-force).

## R-18 — Contratos HTTP (OpenAPI)

- **Decision**: API REST JSON, documentada via OpenAPI gerado pelo
  FastAPI. Recursos principais: `auth`, `projects`, `models`,
  `jobs`, `shares`. Endpoints públicos para visualização (sem
  auth) e endpoints autenticados para o owner.
- **Rationale**: REST simples, OpenAPI auto-gerado elimina o
  problema de spec/code drift. TanStack Query consome OpenAPI
  diretamente no frontend (geração opcional de tipos).
- **Alternatives considered**: GraphQL (rejeitado por overhead
  operacional sem necessidade). gRPC (rejeitado por fricção com
  frontend browser).

## R-19 — Observabilidade mínima

- **Decision**: Logs estruturados (JSON) no backend e no worker,
  incluindo `correlation_id` por request/job, `user_id`,
  `project_id`, `job_id`, `format`, `duration_ms`, `status`. Sem
  APM/metrics server no MVP.
- **Rationale**: Para um sistema com fila assíncrona, a única
  forma de depurar é correlacionar request HTTP e execução do
  worker. JSON estruturado prepara o terreno para um stack de
  observabilidade futuro.
- **Alternatives considered**: OpenTelemetry (rejeitado para
  MVP por adicionar dependência sem provedor).

## R-20 — Segurança de URLs de assets

- **Decision**: URLs públicas de share usam token opaco e
  aleatório (≥128 bits de entropia). Assets (`model.glb`,
  `thumbnail.webp`) servidos por endpoint autenticado **ou** por
  endpoint público com token de share — a estratégia final é
  decidida na fase de implementação, mas o modelo conceitual
  carrega `ShareLink.token`.
- **Rationale**: Token opaco evita enumeração. Permitir servir
  asset via share sem auth é necessário para AR via Quick Look
  (que abre URL diretamente).
- **Alternatives considered**: URL assinada com expiração
  (alternativa razoável; deferida para refinamento de FR).

## R-21 — Stack de testes

- **Decision**: Backend — `pytest` + `httpx`/`pytest-asyncio` para
  integração, `pytest` puro para unit. Frontend — `vitest` +
  `@testing-library/react`. Sem E2E no MVP (suficiente para a
  cobertura pedida pela Constituição princípio 9).
- **Rationale**: pytest é o padrão de fato para FastAPI;
  vitest é o padrão de fato para Vite/React. Integração cobre
  endpoints; unit cobre service/conversion.
- **Alternatives considered**: unittest (rejeitado por ceremony).
  Playwright E2E (deferido por custo de manutenção no MVP).

---

## Decisões de fora-de-escopo do MVP (não produzem artefatos aqui)

- Nenhuma das opções abaixo é introduzida por este plano. Constam
  apenas para registro:
  - Sem MinIO/S3
  - Sem DDD / CQRS / Event Sourcing / Mediator / Repository
    pattern genérico / Unit of Work customizada
  - Sem Clerk / Auth0 / Firebase Auth
  - Sem digital twin / comentários / colaboração / versionamento /
    edição / permissões complexas / BIM avançado
  - Sem RVT/DWG/DXF/SKP no MVP
  - Sem USDZ como formato interno (Quick Look iOS é gerado a
    partir do GLB no lado do viewer; o pipeline de worker entrega
    apenas GLB, e a geração de USDZ é responsabilidade do viewer
    ou de uma extensão de share — **decidido**: fica fora do MVP
    como artefato entregue. AR iOS será explorado na fase de
    implementação sem comprometer este plano).

> **Nota de follow-up**: A Constituição v2.0.0 menciona USDZ/AR iOS
> como derivados do GLB. A geração de USDZ a partir do GLB pode
> acontecer (a) no worker, (b) no viewer, ou (c) on-demand por
> share. Esta decisão é adiada para `/speckit-tasks` ou
> `/speckit-clarify` para não bloquear o plano. O pipeline
> converge para GLB; AR iOS é feature de share/viewer.

---

## Conformidade com a Constituição v2.0.0

| Princípio | Conformidade |
|---|---|
| 1. Simplicidade | ✅ Stack homogênea Python; sem camadas especulativas |
| 2. Vertical Slice | ✅ `features/<name>/{router,schemas,service,persistence,tests}` |
| 3. Backend Python | ✅ FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + Postgres |
| 4. Conversão | ✅ IfcOpenShell + Blender (Trimesh/Open3D/pygltflib explicitamente fora do MVP) |
| 5. Frontend | ✅ React + TS + Vite + TanStack Query + React Router |
| 6. Visualização | ✅ GLB canônico, `<model-viewer>` |
| 7. Armazenamento | ✅ Disco local + abstração `ObjectStorage` |
| 8. Assíncrono | ✅ Celery + Redis |
| 9. Testabilidade | ✅ pytest + vitest; toda feature com unit + integração |
| 10. Proibição de Assunções | ✅ Sem requisitos inventados; USDZ deferido |
| 11. Critério de Conclusão | ✅ Não marca concluído sem testes |
| 12. MVP | ✅ Escopo fechado: upload, conversão, thumbnail, share, view, AR |
