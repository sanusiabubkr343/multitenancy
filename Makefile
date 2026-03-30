# Makefile
.PHONY: help install dev test migrate upgrade downgrade create-migration clean

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make dev              - Run development server"
	@echo "  make test             - Run tests"
	@echo "  make migrate          - Run all migrations"
	@echo "  make upgrade          - Upgrade to latest migration"
	@echo "  make downgrade        - Downgrade one migration"
	@echo "  make create-migration - Create new migration"
	@echo "  make clean            - Clean cache and temporary files"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=html

migrate:
	alembic upgrade head

upgrade:
	alembic upgrade +1

downgrade:
	alembic downgrade -1

create-migration:
	@read -p "Migration message: " message; \
	alembic revision --autogenerate -m "$$message"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

shell:
	docker-compose exec app bash

db-shell:
	docker-compose exec postgres psql -U postgres