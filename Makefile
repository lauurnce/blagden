# Developer entry points. Run `make all` before pushing.

PY := uv run
WEB := pnpm --dir web

.PHONY: setup lint typecheck test golden web-dev web-test all

setup:
	uv sync --locked
	$(WEB) install --frozen-lockfile
	$(PY) pre-commit install

lint:
	$(PY) ruff check src tests scripts
	$(PY) ruff format --check src tests scripts
	$(WEB) lint
	$(WEB) format:check

typecheck:
	$(PY) mypy
	$(WEB) typecheck

test:
	$(PY) pytest

golden:
	$(PY) python scripts/make_synthetic_runs.py
	$(PY) python scripts/make_golden.py
	git diff --exit-code -- tests/fixtures web/tests/golden

web-dev:
	$(WEB) dev

web-test:
	$(WEB) test

all: lint typecheck test web-test golden
