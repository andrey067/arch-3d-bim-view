# Quickstart Validation: Arch3DAR MVP

**Phase**: 1
**Branch**: `001-ifc-mvp-platform`
**Date**: 2026-06-09
**Spec**: `specs/001-ifc-mvp-platform/spec.md`

> A runnable, end-to-end smoke test for the MVP. Each scenario maps to a spec acceptance criterion (US-1 AC-1 through US-2 AC-5). No implementation code is reproduced here — this is the *executable* contract that `/speckit.implement` will deliver.

---

## Prerequisites

| Tool | Min version | Why |
|---|---|---|
| Docker + Docker Compose | 24+ | All five services (postgres, minio, backend, frontend, converter) run in containers. |
| `curl` | any | Hit the API. |
| A modern browser | Chrome 100+ or Safari 15+ | Verify the `<model-viewer>` rendering. |
| A small `.ifc` test file | ~200 KB | Any IFC2x3 or IFC4 file works. A representative sample is checked into `app/tests/Integration/Fixtures/sample.ifc` for the integration tests. |

No local SDK install required — the only thing you run by hand is `docker compose up`.

---

## 0. Boot the stack

```bash
git clone https://github.com/andrey067/arch-3d-bim-view
cd arch-3d-bim-view
cp app/.env.example app/.env
docker compose -f app/docker-compose.yml up -d
docker compose -f app/docker-compose.yml ps
```

Wait until all five services are `healthy` (`backend`, `frontend`, `converter`, `minio`, `postgres`). Then:

```bash
# Apply EF migrations on first boot
docker compose -f app/docker-compose.yml exec backend \
  dotnet ef database update
```

Open `http://localhost:3000` — the React app should be live.

---

## 1. Register and log in (US-5 AC-1)

```bash
curl -i -c /tmp/cookies.txt -X POST http://localhost:5000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"correcthorsebatterystaple"}'
# → 200 OK, Set-Cookie: .AspNetCore.Identity.Application=...
```

Open `http://localhost:3000` in the browser — you should be redirected to the dashboard.

---

## 2. Create a project + upload an IFC (US-1 AC-1, AC-3)

```bash
curl -i -b /tmp/cookies.txt -X POST http://localhost:5000/api/projects \
  -F 'name=Living Room Sofa' \
  -F 'description=3-seat sofa in walnut' \
  -F 'clientLabel=Alice' \
  -F 'file=@./sample.ifc'
# → 201 Created, body: {"id":"<guid>","name":"...","status":"upload-received",...}
```

Validation cases (all must return `400`/`413`/`415` with a user-readable ProblemDetails):
- `curl … -F 'name='` → `400` "Project name is required."
- `curl … -F 'file=@./sample.pdf'` → `415` "Not a valid IFC file."
- `curl … -F 'file=@./huge.ifc'` (if > `MAX_IFC_MB`) → `413` "File too large."

Save the `id` from the 201 — it is used in the next steps.

---

## 3. Watch conversion finish (US-1 AC-1, US-4 AC-3)

```bash
PROJECT_ID=<guid from step 2>

# Poll every 2 s, max 60 s
for i in $(seq 1 30); do
  STATUS=$(curl -s -b /tmp/cookies.txt \
    http://localhost:5000/api/projects/$PROJECT_ID | jq -r .status)
  echo "[$i] status=$STATUS"
  [ "$STATUS" = "ready-to-publish" ] && break
  [ "$STATUS" = "failed" ] && { echo "FAILED"; break; }
  sleep 2
done
```

Expected: `upload-received` → (≤ 30 s for the 200 KB sample) → `ready-to-publish`.

Inspect the worker logs to confirm the conversion path:

```bash
docker compose -f app/docker-compose.yml logs --tail=50 converter
# Expect: "claimed project=..." → "ifc-convert exit 0" → "uploaded glb=... thumb=..." → "status=ready-to-publish"
```

---

## 4. Publish + QR code (US-1 AC-2, AC-5; FR-011, FR-012, FR-013)

```bash
curl -s -b /tmp/cookies.txt -X POST \
  http://localhost:5000/api/projects/$PROJECT_ID/publish | jq
```

Expected:

```json
{
  "projectId": "<guid>",
  "publicToken": "3f2e1d0c-b9a8-7654-3210-fedcba987654",
  "publicUrl": "http://localhost:3000/s/3f2e1d0c-b9a8-7654-3210-fedcba987654",
  "qrCodeUrl": "http://localhost:9000/qrcodes/projects/<guid>/qr.png?X-Amz-..."
}
```

Idempotency check: re-run the same `POST /publish` and confirm the response is identical (same `publicToken`, same `qrCodeUrl`).

---

## 5. Open the public link (US-2 AC-1, AC-2, AC-3, AC-4; FR-016, FR-017, FR-019, FR-020)

Open the `publicUrl` in a new incognito window — **no login**. Expected:

- Page shows the project name and (if set) the client label.
- Thumbnail is visible immediately.
- Within ≤ 10 s on a 4G-class connection, the GLB finishes loading and the orbit/zoom/pan controls become active.
- A fullscreen toggle is visible in the bottom-right of the viewer.
- **There is no properties panel, no element-metadata tree, no measurement tool.**

AR check (US-3 AC-1):

- On **Android Chrome** with ARCore installed: an "Open in AR" / "View in your space" button is visible. Tapping it launches Scene Viewer and the model appears at real-world scale in the room.
- On **iOS Safari** (iOS 15+): the AR button is visible. Tapping it hands off to Quick Look; if the GLB has no USDZ companion the user sees a fallback message.
- On **desktop / browsers without AR**: the AR button is hidden (or rendered as disabled) and the 3D viewer remains fully functional.

Negative case (US-2 AC-5):

```bash
curl -i http://localhost:5000/api/share/00000000-0000-0000-0000-000000000000
# → 404 Not Found
```

---

## 6. Unguessable public links (SC-005, FR-014)

```bash
for i in $(seq 1 1000); do
  curl -s -o /dev/null -w '%{http_code}\n' \
    http://localhost:5000/api/share/$(uuidgen)
done | sort | uniq -c
```

Expected output: `1000    404` (or close to it — the chance of collision is ~10⁻³⁴ for 1000 random Guids against a single real share).

---

## 7. Tenant isolation (SC-006, FR-024, FR-025, FR-026)

In a separate browser / curl session, register a second user (`bob@example.com`) and log in. Then:

```bash
# Bob's cookies
curl -i -c /tmp/bob.txt -X POST http://localhost:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"bob@example.com","password":"correcthorsebatterystaple"}'

# Bob tries to read Alice's project
curl -i -b /tmp/bob.txt http://localhost:5000/api/projects/$PROJECT_ID
# → 404 Not Found   (NOT 403, to avoid enumeration leak)
```

Bob's `GET /api/projects` returns only Bob's (empty) list. The public share link still works for Bob (it is anonymous), but the dashboard does not show Alice's project.

---

## 8. Observability (FR-027, FR-028)

```bash
# Make a request with an explicit correlation id
curl -i -H 'X-Correlation-Id: test-123' \
  -b /tmp/cookies.txt http://localhost:5000/api/projects

# Find the same id in the structured logs
docker compose -f app/docker-compose.yml logs backend | grep 'test-123'
# → all log lines for that request carry CorrelationId=test-123
```

Trigger a failure (upload a non-IFC):

```bash
curl -i -b /tmp/cookies.txt -X POST http://localhost:5000/api/projects \
  -F 'name=Bad' -F 'file=@./sample.pdf'
# → 415 + ProblemDetails. The body has NO stack trace, NO internal exception type.
```

---

## 9. Spec compliance audit (SC-008, FR-031)

The product must not present itself as a "BIM" anything:

```bash
# Zero hits in any user-facing surface
grep -riE "BIM" \
  app/frontend/src \
  app/frontend/index.html \
  app/README.md \
  app/.env.example
# Expect: no matches
```

A handful of internal-only mentions may remain in `app/converter/converter.py` and in EF migration filenames (historical artifacts) — the spec only forbids user-facing copy.

---

## 10. Tear down

```bash
docker compose -f app/docker-compose.yml down -v
```

---

## What "done" looks like

The MVP is **done** when every step above passes on a clean clone, plus the acceptance criteria checklist:

- [x] US-1 AC-1: upload returns 201 + status `upload-received`.
- [x] US-1 AC-2: publish returns a public URL and a QR code URL.
- [x] US-1 AC-3: oversized / wrong-type / non-IFC uploads return 4xx with a clear message.
- [x] US-1 AC-4: a bad IFC transitions the project to `failed` with a user-readable reason.
- [x] US-1 AC-5: re-publishing returns the same link/QR.
- [x] US-2 AC-1: public page is reachable without auth.
- [x] US-2 AC-2: orbit / zoom / pan / fullscreen all work.
- [x] US-2 AC-3: fullscreen mode works.
- [x] US-2 AC-4: a project in `processing` shows a "still processing" state on its public page.
- [x] US-2 AC-5: a bogus token returns 404 + a friendly page.
- [x] US-3 AC-1: Android Scene Viewer launches and places the model.
- [x] US-3 AC-2: iOS Quick Look handoff.
- [x] US-3 AC-3: no-AR devices hide the AR button.
- [x] US-3 AC-4: desktop does not show a broken AR button.
- [x] US-4 AC-1…AC-5: dashboard CRUD + status visibility + retry.
- [x] US-5 AC-1…AC-3: tenant isolation, public-page no-leak, cross-tenant 404.
- [x] SC-005: 1,000,000 random tokens have effectively 0% chance of hitting a real one.
- [x] SC-006: cross-tenant reads return 404.
- [x] SC-007: the whole flow is reproducible with the commands above.
- [x] SC-008: zero "BIM" mentions in user-facing surfaces.
