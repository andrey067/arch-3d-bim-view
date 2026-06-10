.PHONY: up down logs restart ps build-backend build-frontend test-backend test-frontend e2e audit-bim clean

COMPOSE := docker compose -f app/docker-compose.yml

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

build-backend:
	cd app/backend && dotnet build

build-frontend:
	cd app/frontend && npm run build

test-backend:
	cd app/tests/backend && dotnet test

test-frontend:
	cd app/frontend && npx vitest run

e2e:
	cd app/frontend && npx playwright test

# FR-031 / SC-008: zero "BIM platform/collaboration/coordination/metadata/management/engineering"
# mentions in user-facing surfaces. Negation contexts ("not a BIM platform", "is not a
# coordination tool") are allowed because they are explicitly disclaiming the term.
audit-bim:
	@bash -c 'set -e; \
	  hits=$$(grep -rEi "BIM (platform|collaboration|coordination|metadata|management|engineering)" \
	    app/frontend/src \
	    app/frontend/index.html \
	    app/README.md \
	    app/.env.example 2>/dev/null \
	    | grep -vEi "not a BIM|is not a BIM|not a coordination|is not a coordination|no .* BIM|never BIM|without BIM" \
	    || true); \
	  if [ -n "$$hits" ]; then \
	    echo "BIM terminology found in user-facing surfaces:"; \
	    echo "$$hits"; \
	    exit 1; \
	  else \
	    echo "OK: no forbidden BIM terminology in user-facing surfaces."; \
	  fi'

clean:
	cd app/backend && rm -rf bin obj
	cd app/frontend && rm -rf dist node_modules
	$(COMPOSE) down -v
