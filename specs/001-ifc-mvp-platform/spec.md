# Product Context: App 3D Viewer

**Feature Branch**: `001-ifc-mvp-platform` *(directory name is legacy; to be renamed when the next feature lifecycle is opened)*
**Updated**: 2026-06-11
**Status**: Draft — Product context / vision reset
**Input**: Reset of the product vision to **App 3D Viewer** — a generic 3D viewer, not a BIM platform.

> **Scope of this document**
>
> This file captures **only the product context and vision**: the problem, the
> solution, the target audience, the main flow, what is in scope, what is out of
> scope, input formats, internal format, and visual quality priorities.
>
> It deliberately does **not** contain:
>
> - Functional requirements (FRs)
> - Architecture or stack decisions
> - Tasks or backlog
> - Data model or entity definitions
> - Folder structure or component decomposition
> - API contracts
> - Diagrams
>
> Those are produced in subsequent Spec Kit phases (`/speckit-clarify`,
> `/speckit-plan`, `/speckit-tasks`) once this context is agreed.
>
> The project Constitution (`.specify/memory/constitution.md` v2.0.0) is the
> governing document for stack, structure, and principles. The Constitution has
> already been updated in a prior step and is not re-declared here.

---

## Product Name

**App 3D Viewer**

---

## Problem

Architects, interior designers, cabinet makers, custom-furniture designers and
3D modeling professionals struggle to share projects with their clients in a
simple way.

Their clients typically:

- do not own specialized 3D software
- do not know how to open technical files
- only use a web browser or a smartphone

This creates friction in project approval.

---

## Solution

Allow professionals to upload 3D models to the platform.

The platform:

1. receives the uploaded file,
2. processes the model,
3. generates an optimized web-ready version,
4. exposes a public link.

The client opens the link in any browser and views the 3D model.

When supported by the device, the client can also view the model in
**Augmented Reality**.

---

## Target Audience

### Primary

- Architects
- Interior designers
- Cabinet makers
- Custom-furniture designers

### Secondary

- Engineers
- Construction companies
- Architecture offices

---

## Main Flow

1. User uploads a file.
2. System processes the model.
3. System generates GLB.
4. System generates a thumbnail.
5. System generates a public link.
6. Client opens the link.
7. Client views the 3D model.
8. Client uses AR when available.

---

## Value Delivered

- Reduce the effort required to share 3D projects.
- Eliminate the need for specialized software on the client side.
- Allow fast and accessible 3D visualization.

---

## What the Product Is NOT

The App 3D Viewer is **not**:

- a full BIM platform
- Revit Web
- Navisworks Web
- Solibri Web
- a CAD system
- a 3D editor
- a modeling tool

---

## Out of MVP

The following are explicitly **not** part of the MVP and must not be assumed
in this phase:

- Model editing
- Real-time collaboration
- Advanced version control
- Model comments
- BIM measurements
- Clash detection
- Full IFC tree
- Advanced BIM properties
- IFC classification
- Digital twin

---

## In MVP

The MVP must deliver **only**:

- upload
- processing
- conversion to GLB
- thumbnail
- sharing
- web visualization
- AR visualization

---

## Input Formats

The system must be prepared to work with the following input formats:

- SKP
- RVT
- DWG
- DXF
- DAE
- STL
- OBJ
- IFC

However, **the actual conversion path and effective support for each format
will be defined later, during requirement refinement**.

This step must **not** assume full support for all of these formats.

---

## Internal Format

The platform's canonical internal format is:

**GLB**

All processing must converge to GLB for both visualization and AR.

---

## Visual Quality

The primary goal of conversion is to preserve:

1. materials
2. textures
3. UV mapping

**Visual fidelity has priority over BIM metadata.**

---

## Notes for the Next Phases

The following items are intentionally **out of scope** for this document and
will be addressed in subsequent Spec Kit phases:

- Detailed functional requirements (will be produced by `/speckit-clarify`
  and/or `/speckit-plan`).
- Architecture and stack details (governed by the Constitution v2.0.0).
- Tasks and backlog (will be produced by `/speckit-tasks`).
- Data model, entities and validation rules (will be produced by
  `/speckit-plan` and `data-model.md`).
- API contracts (will be produced by `/speckit-plan` and `contracts/`).
- Acceptance scenarios, edge cases, success criteria (will be produced by
  `/speckit-clarify` and `/speckit-plan`).

The directory name `001-ifc-mvp-platform` is a legacy of the previous
framing. Renaming the directory is also deferred to the next spec lifecycle
to avoid disturbing in-flight work.

---

**Ready for**: `/speckit-clarify` (to derive detailed requirements) or
`/speckit-plan` (to derive the implementation plan), only when the user
decides to move forward.
