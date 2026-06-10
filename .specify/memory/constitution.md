<!--
  Sync Impact Report:
  ==================
  Version change: 0.0.0 → 1.0.0 (MAJOR: first substantive constitution from template)
  
  Modified principles:
  - [PRINCIPLE_1_NAME] → I. Clean Code & MVP Pragmatism
  - [PRINCIPLE_2_NAME] → II. Meaningful Naming & Structure
  - [PRINCIPLE_3_NAME] → III. Small Units & Single Responsibility
  - [PRINCIPLE_4_NAME] → IV. Tests Mirror Structure (Backend/Frontend Separation)
  - [PRINCIPLE_5_NAME] → V. Self-Documenting Code & Minimal Comments
  
  Added sections:
  - Section 2: Project Structure & Organization Standards
  - Section 3: Development Workflow & Quality Gates
  - Governance section with amendment/versioning rules
  
  Removed sections: (none)
  
  Templates requiring updates:
  - .specify/templates/constitution-template.md (✅ not user-facing, template preserved)
  - .specify/templates/plan-template.md (✅ structure examples align, no changes needed)
  - .specify/templates/spec-template.md (✅ no constitution-specific constraints)
  - .specify/templates/tasks-template.md (✅ path conventions mention frontend/backend — already aligned)
  - .specify/templates/checklist-template.md (✅ generic, no changes needed)
  
  Follow-up TODOs: (none)
-->

# Arch3DAR Constitution

## Core Principles

### I. Clean Code & MVP Pragmatism

Code MUST be clean, simple, and sufficient. Every abstraction, class, or
dependency MUST justify its existence — no over-engineering for hypothetical
future needs. YAGNI (You Ain't Gonna Need It) applies strictly. When in doubt,
prefer the simpler solution that satisfies current requirements.

**Rationale**: This is an MVP. Premature abstraction and speculative
generality are the primary sources of unnecessary complexity. Clean code is
not about more layers — it is about clarity at the right level of
abstraction.

### II. Meaningful Naming & Structure

Names MUST reveal intent. Functions, classes, variables, files, and routes
MUST have unambiguous, pronounceable names that communicate purpose without
requiring a comment. Avoid abbreviations (except universally accepted ones
like `id`, `url`, `http`). Project structure MUST follow a consistent,
predictable layout so that any file can be located by its logical role.

### III. Small Units & Single Responsibility

Every function, method, or component MUST do one thing and one thing only.
If a function exceeds 20–30 lines or accumulates multiple responsibilities,
split it. Components (React) MUST have a single responsibility — extract
child components when a parent grows beyond 100–150 lines. No god objects,
no monster functions.

### IV. Tests Mirror Structure (Backend/Frontend Separation)

Tests MUST be organized to mirror source code structure. All tests live under
`app/tests/` with two top-level domains:
- **`app/tests/backend/`** — Tests for ASP.NET Core backend (`app/backend/`)
- **`app/tests/frontend/`** — Tests for React frontend (`app/frontend/`)

Within each domain, subdivide by test type as needed (unit, integration,
contract). Each test MUST be independently runnable. Tests are not optional
— they are the specification of correct behavior.

**Rationale**: Separating backend and frontend tests prevents framework
cross-contamination, makes CI faster (parallel execution), and keeps test
concerns focused. This is an MVP — the test layout must be simple,
scannable, and maintainable.

### V. Self-Documenting Code & Minimal Comments

Code SHOULD be self-documenting. Comments MUST explain WHY, not WHAT or HOW
— those should be evident from clean code. Do NOT write comments that parrot
the code. Do NOT leave commented-out code — delete it. If code is unclear
enough to need a "what" comment, refactor it instead.

## Project Structure & Organization Standards

The repository follows a web-application layout:

```
app/
├── backend/           # ASP.NET Core 9 API
├── frontend/          # React + Vite BIM viewer
├── converter/         # IFC-to-GLB conversion worker
├── tests/
│   ├── backend/       # Backend tests (unit, integration, contract)
│   └── frontend/      # Frontend tests (unit, integration, e2e)
├── nginx/             # Reverse proxy configuration
├── docker-compose.yml
└── .env
```

- All source code resides under `app/`. No source files outside `app/`.
- Tests reside exclusively under `app/tests/`, mirroring the source domain.
- Infrastructure config (Docker, nginx, CI) belongs in the root or `app/`
  root — do not scatter configs inside `backend/` or `frontend/`.
- Environment templates go in `.env.example` at the applicable level.

## Development Workflow & Quality Gates

1. **Test-First Mindset**: Write a failing test before implementing any
   feature or fix. This is strongly recommended for all changes.
2. **All Tests MUST Pass** before merging into the main branch.
3. **Linting MUST Pass**: Frontend code MUST pass ESLint. Backend code MUST
   pass `dotnet format` or equivalent.
4. **No Dead Code**: Unused imports, commented-out code, and unreachable
   branches MUST be removed before commit.
5. **Each PR MUST Include Tests**: A PR that introduces new functionality
   without corresponding tests will be rejected.
6. **Complexity Requires Justification**: If the Constitution Check in the
   plan identifies a complexity violation, the PR MUST include a documented
   justification explaining why a simpler approach is insufficient.

## Governance

This Constitution is the governing document for all development practices,
code style, and project structure decisions. It supersedes informal habits
and personal preferences.

### Amendment Procedure

1. Propose a change to `.specify/memory/constitution.md` via a Pull Request.
2. Document the rationale, impact on existing code, and migration path.
3. At least one approving review is required.
4. Update `LAST_AMENDED_DATE` and increment `CONSTITUTION_VERSION` per the
   versioning policy below.

### Versioning Policy

- **MAJOR** (x.0.0): Backward-incompatible principle removals or
  redefinitions.
- **MINOR** (0.x.0): New principle or materially expanded guidance.
- **PATCH** (0.0.x): Clarifications, wording fixes, non-semantic refinements.

### Compliance Review

Every `/speckit-plan` execution MUST include a Constitution Check step.
Violations MUST be documented in the Complexity Tracking section of the plan.
Persistent or severe violations MAY block implementation until resolved.

**Version**: 1.0.0 | **Ratified**: 2026-06-09 | **Last Amended**: 2026-06-09
