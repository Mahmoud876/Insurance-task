ifeq ($(OS),Windows_NT)
    VENV_DIR := .venv
    VENV_BIN := $(VENV_DIR)/Scripts
    PYTHON_HOST ?= python
else
    VENV_DIR := .venv
    VENV_BIN := $(VENV_DIR)/bin
    PYTHON_HOST ?= python3
endif

VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

.PHONY: venv setup lint test compose-up compose-down migrate seed clean

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON_HOST) -m venv $(VENV_DIR); \
	fi

setup: venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"
	$(VENV_BIN)/pre-commit install

lint:
	$(VENV_BIN)/ruff check .
	$(VENV_BIN)/mypy .
	$(VENV_BIN)/lint-imports

test:
	$(VENV_BIN)/pytest

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v

migrate:
	@echo "No migrations to run yet."

seed:
	@echo "No seed data to insert yet."