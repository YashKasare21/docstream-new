# =============================================================================
# DocStream — Hybrid Monorepo Orchestrator
# =============================================================================
#
# A Python core + Python CLI + Python FastAPI backend + Next.js frontend,
# glued together with this Makefile (no Nx, Turborepo, Pants, or Bazel).
#
# Common targets:
#   make install      Install everything (Python venvs + npm modules)
#   make dev          Run API and Web concurrently
#   make dev-api      Run only the FastAPI backend
#   make dev-web      Run only the Next.js frontend
#   make test         Run Python tests across all packages
#   make lint         Lint Python and JavaScript code
#   make clean        Remove venvs, build artifacts, caches
# =============================================================================

PYTHON ?= python3
PIP    ?= pip
NPM    ?= npm

CORE_DIR := packages/core-python
CLI_DIR  := apps/cli-python
API_DIR  := apps/api-python
WEB_DIR  := apps/web-node

VENV_CLI := $(CLI_DIR)/.venv
VENV_API := $(API_DIR)/.venv

CLI_PY := $(VENV_CLI)/bin/python
CLI_PIP := $(VENV_CLI)/bin/pip
API_PY := $(VENV_API)/bin/python
API_PIP := $(VENV_API)/bin/pip

.PHONY: help install install-cli install-api install-web \
        dev dev-api dev-web \
        test test-core test-cli test-api test-python \
        lint lint-python lint-py lint-web \
        format format-python \
        docker-build docker-up docker-down clean

# Default target — show help.
help:
	@echo "DocStream monorepo — available targets:"
	@echo ""
	@echo "  make install      Install Python venvs (cli, api) + web npm modules"
	@echo "  make dev          Run FastAPI backend and Next.js frontend concurrently"
	@echo "  make dev-api      Run only the FastAPI backend"
	@echo "  make dev-web      Run only the Next.js frontend"
	@echo "  make test         Run all Python tests (core + cli + api)"
	@echo "  make test-python  Run core + API tests"
	@echo "  make lint         Lint Python and JS sources"
	@echo "  make lint-python  Lint Python sources only"
	@echo "  make lint-web     Lint Web/Next.js sources only"
	@echo "  make format       Auto-format Python sources with ruff"
	@echo "  make format-python  Alias for format"
	@echo "  make clean        Remove venvs, build artifacts, caches"
	@echo ""

# -----------------------------------------------------------------------------
# Install
# -----------------------------------------------------------------------------

install: install-cli install-api install-web
	@echo ""
	@echo "✓ Monorepo install complete."
	@echo "  Run 'make dev' to start API + Web concurrently."

install-cli:
	@echo "→ Setting up CLI venv at $(VENV_CLI)..."
	$(PYTHON) -m venv $(VENV_CLI)
	$(CLI_PIP) install --upgrade pip
	$(CLI_PIP) install -e $(CORE_DIR)
	$(CLI_PIP) install -e $(CLI_DIR)
	$(CLI_PIP) install --force-reinstall --no-deps -e $(CORE_DIR)
	@echo "✓ CLI installed."

install-api:
	@echo "→ Setting up API venv at $(VENV_API)..."
	$(PYTHON) -m venv $(VENV_API)
	$(API_PIP) install --upgrade pip
	$(API_PIP) install -e $(CORE_DIR)
	$(API_PIP) install -e $(API_DIR)
	$(API_PIP) install --force-reinstall --no-deps -e $(CORE_DIR)
	@echo "✓ API installed."

install-web:
	@echo "→ Installing web dependencies..."
	cd $(WEB_DIR) && $(NPM) install
	@echo "✓ Web installed."

# -----------------------------------------------------------------------------
# Dev servers
# -----------------------------------------------------------------------------

dev: install-api install-web
	@echo "→ Starting API + Web concurrently (Ctrl-C to stop both)..."
	@trap 'kill 0' INT TERM EXIT; \
		$(MAKE) -s dev-api & \
		$(MAKE) -s dev-web & \
		wait

dev-api: install-api
	cd $(API_DIR) && ./.venv/bin/uvicorn docstream_api.main:app --reload --host 0.0.0.0 --port 8000

dev-web: install-web
	cd $(WEB_DIR) && $(NPM) run dev

# -----------------------------------------------------------------------------
# Test
# -----------------------------------------------------------------------------

test: test-core test-cli test-api

test-python: test-core test-api
	@echo "✓ All Python tests complete."

# Core tests are exercised through the CLI venv (which has docstream-core installed editable).
test-core:
	@echo "→ Running core tests..."
	cd $(CORE_DIR) && ../../$(VENV_CLI)/bin/pytest tests/

test-cli:
	@echo "→ Running CLI tests..."
	cd $(CLI_DIR) && ./.venv/bin/pytest tests/

test-api:
	@echo "→ Running API tests..."
	cd $(API_DIR) && ./.venv/bin/pytest tests/

# -----------------------------------------------------------------------------
# Lint / format
# -----------------------------------------------------------------------------

lint: lint-python lint-web

# Aliases
lint-python: lint-py
format-python: format

lint-py:
	@echo "→ Linting Python sources with ruff..."
	cd $(CORE_DIR) && ../../$(VENV_CLI)/bin/ruff check . || true
	cd $(CLI_DIR)  && ./.venv/bin/ruff check . || true
	cd $(API_DIR)  && ./.venv/bin/ruff check . || true

lint-web:
	@echo "→ Linting web sources..."
	cd $(WEB_DIR) && $(NPM) run lint || true

format:
	cd $(CORE_DIR) && ../../$(VENV_CLI)/bin/ruff format .
	cd $(CLI_DIR)  && ./.venv/bin/ruff format .
	cd $(API_DIR)  && ./.venv/bin/ruff format .

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down

# -----------------------------------------------------------------------------
# Clean
# -----------------------------------------------------------------------------

clean:
	@echo "→ Removing virtual envs and build artifacts..."
	rm -rf $(VENV_CLI) $(VENV_API)
	rm -rf $(CORE_DIR)/dist $(CORE_DIR)/build $(CORE_DIR)/*.egg-info
	rm -rf $(CLI_DIR)/dist  $(CLI_DIR)/build  $(CLI_DIR)/*.egg-info
	rm -rf $(API_DIR)/dist  $(API_DIR)/build  $(API_DIR)/*.egg-info
	rm -rf $(WEB_DIR)/.next $(WEB_DIR)/node_modules
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +
	@echo "✓ Clean complete."
