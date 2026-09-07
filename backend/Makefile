ifeq ($(OS),Windows_NT)
    VENV_DIR := .venv
    VENV_BIN := $(VENV_DIR)/Scripts
    PYTHON_HOST ?= python
    NPM := npm.cmd
else
    VENV_DIR := .venv
    VENV_BIN := $(VENV_DIR)/bin
    PYTHON_HOST ?= python3
    NPM := npm
endif

VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

.PHONY: venv setup install dev build lint lint-fix test compose-up compose-down migrate migrate-down seed clean help ci

help:
	@echo "Available commands:"
	@echo "  make setup        Set up virtualenv, python deps, pre-commit, and npm packages"
	@echo "  make install      Install frontend npm dependencies"
	@echo "  make dev          Start local frontend dev server"
	@echo "  make build        Build frontend production assets"
	@echo "  make lint         Run backend (ruff, mypy) and frontend linters"
	@echo "  make test         Run backend (pytest) and frontend tests"
	@echo "  make compose-up   Start Docker Compose stack"
	@echo "  make compose-down Tear down Docker Compose stack"
	@echo "  make migrate      Run database migrations (alembic upgrade head)"
	@echo "  make migrate-down Roll back last database migration (alembic downgrade -1)"
	@echo "  make seed         Seed database data"
	@echo "  make clean        Remove virtualenvs, build artifacts, and test caches"

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON_HOST) -m venv $(VENV_DIR); \
	fi

setup: venv install
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"
	$(VENV_BIN)/pre-commit install

install:
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) install; else echo "Skipping frontend install (no package.json)"; fi

dev:
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) run dev; else echo "No frontend package.json found"; fi

build:
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) run build; else echo "No frontend package.json found"; fi

lint:
	$(VENV_BIN)/ruff check app tests
	$(VENV_BIN)/mypy app
	$(VENV_BIN)/lint-imports
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) run lint; fi

lint-fix:
	$(VENV_BIN)/ruff check --fix app tests
	$(VENV_BIN)/mypy app | $(VENV_BIN)/mypy-baseline filter

test:
	$(VENV_BIN)/pytest tests/ -v --cov=app --cov-report=term-missing
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) run test; fi


compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v

migrate:
	$(VENV_BIN)/alembic upgrade head

migrate-down:
	$(VENV_BIN)/alembic downgrade -1

seed:
	$(VENV_PYTHON) -m app.modules.reference.seed_dev_data

clean:
	rm -rf $(VENV_DIR) node_modules ../frontend/node_modules .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml dist build *.egg-info

ci: venv
	@echo "==> 1/5 Running Ruff..."
	$(VENV_BIN)/ruff check .
	@echo "==> 2/5 Running Mypy (Strict CI Check)..."
	$(VENV_BIN)/mypy .
	@echo "==> 3/5 Running Import Linter..."
	PYTHONPATH=. $(VENV_BIN)/lint-imports
	@echo "==> 4/5 Running Pytest & Migrations..."
	DATABASE_URL="postgresql://postgres:postgres@localhost:5432/scrubber_test" $(VENV_BIN)/pytest
	DATABASE_URL="postgresql://postgres:postgres@localhost:5432/scrubber_test" $(VENV_BIN)/alembic upgrade head
	DATABASE_URL="postgresql://postgres:postgres@localhost:5432/scrubber_test" $(VENV_BIN)/alembic downgrade -1
	DATABASE_URL="postgresql://postgres:postgres@localhost:5432/scrubber_test" $(VENV_BIN)/alembic upgrade head
	@echo "==> 5/5 Building Frontend..."
	@if [ -f "../frontend/package.json" ]; then cd ../frontend && $(NPM) run build; fi
	@echo "✅ All CI checks passed locally!"
