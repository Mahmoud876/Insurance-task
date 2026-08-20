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

.PHONY: venv setup install dev build lint test compose-up compose-down migrate seed clean help

help:
	@echo "Available commands:"
	@echo "  make setup        Set up virtualenv, python deps, pre-commit, and npm packages"
	@echo "  make install      Install frontend npm dependencies"
	@echo "  make dev          Start local frontend dev server"
	@echo "  make build        Build frontend production assets"
	@echo "  make lint         Run backend (ruff, mypy, import-linter) and frontend linters"
	@echo "  make test         Run backend (pytest) and frontend tests"
	@echo "  make compose-up   Start Docker Compose stack"
	@echo "  make compose-down Tear down Docker Compose stack"
	@echo "  make migrate      Run database migrations"
	@echo "  make seed         Seed database data"
	@echo "  make clean        Remove .venv and node_modules"

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON_HOST) -m venv $(VENV_DIR); \
	fi

setup: venv install
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e "./api[dev]"
	$(VENV_BIN)/pre-commit install

install:
	@if [ -f "frontend/package.json" ]; then cd frontend && $(NPM) install; else echo "Skipping frontend install (no package.json)"; fi

dev:
	@if [ -f "frontend/package.json" ]; then cd frontend && $(NPM) run dev; else echo "No frontend package.json found"; fi

build:
	@if [ -f "frontend/package.json" ]; then cd frontend && $(NPM) run build; else echo "No frontend package.json found"; fi

lint:
	$(VENV_BIN)/ruff check api
	$(VENV_BIN)/mypy api
	$(VENV_BIN)/lint-imports --config api/pyproject.toml
	@if [ -f "frontend/package.json" ]; then cd frontend && $(NPM) run lint; fi

test:
	$(VENV_BIN)/pytest api
	@if [ -f "frontend/package.json" ]; then cd frontend && $(NPM) run test; fi

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v

migrate:
	@echo "No migrations to run yet."

seed:
	$(VENV_BIN)/python app/db/seed_reference_data.py

clean:
	rm -rf $(VENV_DIR) node_modules frontend/node_modules .pytest_cache .mypy_cache
