.PHONY: setup setup-backend setup-frontend lint lint-backend lint-frontend test test-backend test-frontend format check dev dev-backend dev-frontend clean

# ── Setup ────────────────────────────────────────────────────────────────────

setup: setup-backend setup-frontend

setup-backend:
	cd backend && uv sync

setup-frontend:
	cd frontend && npm install

# ── Lint ─────────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check app tests
	cd backend && uv run ruff format --check app tests
	cd backend && uv run mypy app

lint-frontend:
	cd frontend && npm run lint
	cd frontend && npm run typecheck

# ── Test ─────────────────────────────────────────────────────────────────────

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest tests -v

test-frontend:
	@echo "No frontend tests yet"

# ── Format ───────────────────────────────────────────────────────────────────

format:
	cd backend && uv run ruff format app tests
	cd backend && uv run ruff check app tests --fix

# ── Check (lint + test) ─────────────────────────────────────────────────────

check: lint test

# ── Dev servers ──────────────────────────────────────────────────────────────

dev-backend:
	cd backend && uv run uvicorn app.server:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Clean ────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next
