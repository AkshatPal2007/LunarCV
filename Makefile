.PHONY: help install dev dev-backend dev-frontend lint test frontend-check browser-test real-browser-test build register inspect models release-check clean docker-build docker-up docker-down docker-logs
help:
	@echo "See COMMANDS.md for all commands and CLI flags."
	@echo "install dev dev-backend dev-frontend lint test frontend-check browser-test real-browser-test build register inspect models release-check clean docker-build docker-up docker-down docker-logs"
install:
	cd backend && uv sync --frozen
	cd frontend && npm ci
dev:
	python3 scripts/dev.py
dev-backend:
	cd backend && uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
dev-frontend:
	cd frontend && npm run dev
lint:
	cd backend && uv run --frozen ruff check .
	cd frontend && npm run lint
test:
	cd backend && uv run --frozen pytest tests ../tests -q
frontend-check:
	cd frontend && npm run typecheck && npm run lint && npm run format:check && npm run build
browser-test:
	cd frontend && npm test
real-browser-test:
	cd frontend && LUNARCV_REAL_DATA=1 npm test
build:
	backend/.venv/bin/python backend/scripts/build_wheel.py
	cd frontend && npm run build
register:
	backend/.venv/bin/lunarcv-register
inspect:
	backend/.venv/bin/lunarcv-inspect $(RUN)
models:
	backend/.venv/bin/python backend/scripts/prefetch_models.py --features aliked
release-check:
	backend/.venv/bin/python backend/scripts/release_check.py
clean:
	python3 scripts/clean.py
docker-build:
	docker compose build
docker-up:
	docker compose up -d
docker-down:
	docker compose down
docker-logs:
	docker compose logs -f
