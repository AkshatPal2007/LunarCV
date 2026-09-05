.PHONY: help install dev-backend dev-frontend dev lint test clean docker-build docker-up docker-down docker-down-volumes docker-logs

help:
	@echo "LunarCV - Available commands:"
	@echo "  make install        - Install backend and frontend dependencies"
	@echo "  make dev-backend    - Run backend dev server"
	@echo "  make dev-frontend   - Run frontend dev server"
	@echo "  make dev            - Run both backend and frontend in parallel"
	@echo "  make lint           - Run linter on backend code"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean generated files and caches"
	@echo "  make docker-build         - Build Docker images"
	@echo "  make docker-up            - Start services with docker-compose"
	@echo "  make docker-down          - Stop services"
	@echo "  make docker-down-volumes  - Stop services and remove volumes"
	@echo "  make docker-logs          - View logs from services"

install:
	@echo "Installing backend dependencies..."
	cd backend && uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	python scripts/dev.py

lint:
	cd backend && uv run ruff check .

test:
	cd backend && uv run pytest

clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv
	rm -rf data/uploads/* data/results/*

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started:"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Frontend: http://localhost:5173"

docker-down:
	docker-compose down

docker-down-volumes:
	docker-compose down -v

docker-logs:
	docker-compose logs -f
