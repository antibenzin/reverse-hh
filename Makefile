.PHONY: dev test lint migrate down

dev:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && python -m pytest

lint:
	cd backend && python -m ruff check .

migrate:
	cd backend && alembic upgrade head
