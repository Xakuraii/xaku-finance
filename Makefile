# XakuFinance developer commands.
# Activate the backend virtualenv first, or override PYTHON.

PYTHON ?= python
MANAGE := $(PYTHON) manage.py
COMPOSE := docker compose

.PHONY: help install db-up db-down migrate makemigrations test lint fmt typecheck schema check run

help:
	@echo "install        install backend dependencies"
	@echo "db-up          start Postgres and Redis"
	@echo "db-down        stop Postgres and Redis"
	@echo "migrate        apply database migrations"
	@echo "makemigrations create migrations"
	@echo "test           run the test suite"
	@echo "lint           run ruff"
	@echo "fmt            format with ruff"
	@echo "typecheck      run mypy"
	@echo "schema         regenerate docs/openapi.yaml and validate"
	@echo "check          lint + typecheck + test"
	@echo "run            start the development server"

install:
	$(PYTHON) -m pip install -e ".[dev]"

db-up:
	$(COMPOSE) up -d postgres redis

db-down:
	$(COMPOSE) down

migrate:
	cd backend && $(MANAGE) migrate

makemigrations:
	cd backend && $(MANAGE) makemigrations

test:
	cd backend && $(PYTHON) -m pytest -q

lint:
	cd backend && $(PYTHON) -m ruff check .

fmt:
	cd backend && $(PYTHON) -m ruff format .

typecheck:
	cd backend && $(PYTHON) -m mypy apps

schema:
	cd backend && $(MANAGE) spectacular --file ../docs/openapi.yaml --validate

check: lint typecheck test

run:
	cd backend && $(MANAGE) runserver 8000
