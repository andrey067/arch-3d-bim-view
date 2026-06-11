.PHONY: up down logs restart ps build-backend build-frontend test-backend test-frontend clean migrate

COMPOSE := docker compose -f infra/docker/docker-compose.yml

# --- Docker ---
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

restart:
	$(COMPOSE) restart

ps:
	$(COMPOSE) ps

# --- Backend ---
build-backend:
	$(COMPOSE) build backend

test-backend:
	cd apps/backend && python -m pytest -q

migrate:
	$(COMPOSE) exec backend alembic upgrade head

# --- Frontend ---
build-frontend:
	$(COMPOSE) build frontend

test-frontend:
	cd apps/frontend && npm test

# --- Dev (local, no Docker) ---
dev-backend:
	cd apps/backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd apps/frontend && npm run dev

# --- Cleanup ---
clean:
	$(COMPOSE) down -v --remove-orphans
	cd apps/backend && rm -rf .pytest_cache .mypy_cache .ruff_cache
	cd apps/frontend && rm -rf dist node_modules

# --- Audit (FR-031: no BIM terminology in user-facing surfaces) ---
audit-bim:
	@bash -c 'set -e; \
	  hits=$$(grep -rEi "BIM (platform|collaboration|coordination|metadata|management|engineering)" \
	    apps/frontend/src \
	    apps/frontend/index.html 2>/dev/null \
	    | grep -vEi "not a BIM|is not a BIM|not a coordination|is not a coordination|no .* BIM|never BIM|without BIM" \
	    || true); \
	  if [ -n "$$hits" ]; then \
	    echo "BIM terminology found in user-facing surfaces:"; \
	    echo "$$hits"; \
	    exit 1; \
	  else \
	    echo "OK: no forbidden BIM terminology in user-facing surfaces."; \
	  fi'
