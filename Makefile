.PHONY: help dev up down logs clean build migrate test

help:
	@echo "Curio - Available Commands:"
	@echo ""
	@echo "  make dev          - Start development environment"
	@echo "  make up           - Start production environment"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View logs"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make build        - Build Docker images"
	@echo "  make migrate      - Run database migrations"
	@echo "  make test         - Run tests"
	@echo "  make backup       - Backup database"
	@echo "  make restore      - Restore database from backup"
	@echo ""

dev:
	@echo "Starting development environment..."
	docker-compose -f .devcontainer/docker-compose.yml up -d

up:
	@echo "Starting production environment..."
	docker-compose up -d

down:
	@echo "Stopping all services..."
	docker-compose down

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f

build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

migrate:
	@echo "Running database migrations..."
	docker-compose exec backend alembic upgrade head

test:
	@echo "Running tests..."
	cd backend && pytest
	cd frontend && npm test

backup:
	@echo "Backing up database..."
	@mkdir -p backups
	docker-compose exec db pg_dump -U curio curio > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup completed!"

restore:
	@echo "Restoring database from latest backup..."
	@latest=$$(ls -t backups/*.sql | head -1); \
	if [ -z "$$latest" ]; then \
		echo "No backup files found!"; \
		exit 1; \
	fi; \
	echo "Restoring from $$latest"; \
	cat $$latest | docker-compose exec -T db psql -U curio curio
	@echo "Restore completed!"
