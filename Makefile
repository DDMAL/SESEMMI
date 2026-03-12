COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_DEV  = $(COMPOSE_BASE) -f docker-compose.dev.yml
COMPOSE_TEST = $(COMPOSE_BASE) -f docker-compose.test.yml
COMPOSE_PROD = $(COMPOSE_BASE) -f docker-compose.prod.yml

.PHONY: dev dev-build dev-down dev-clean test test-build test-llm prod prod-build prod-down shell shell-llm format-llm format-llm-check

# ── Development ───────────────────────────────────────────────────────────────
dev:
	$(COMPOSE_DEV) up

dev-run:
	$(COMPOSE_DEV) up --build

dev-down:
	$(COMPOSE_DEV) down

dev-clean:
	$(COMPOSE_DEV) down -v

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	$(COMPOSE_TEST) run --rm app

test-build:
	$(COMPOSE_TEST) run --rm --build app

test-llm:
	cd llm-service && uv run pytest

format-llm:
	cd llm-service && uv run black .

format-llm-check:
	cd llm-service && uv run black --check .

# ── Production ────────────────────────────────────────────────────────────────
prod:
	$(COMPOSE_PROD) up -d

prod-build:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

# ── Utilities ─────────────────────────────────────────────────────────────────
shell:
	docker exec -it sesemmi-app sh

shell-llm:
	docker exec -it sesemmi-llm sh

