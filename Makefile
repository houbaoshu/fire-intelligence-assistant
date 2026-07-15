.PHONY: help dev backend-dev frontend-dev docker-build docker-up docker-down test lint migrate migrate-create

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: docker-up ## Start all services with Docker

backend-dev: ## Start backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Start frontend in development mode
	cd frontend && bun dev

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start Docker services
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

test: ## Run backend tests
	cd backend && pytest tests/ -v

lint: ## Run linters
	cd backend && ruff check app/
	cd frontend && bunx tsc --noEmit

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration
	cd backend && alembic revision --autogenerate -m "$(msg)"
