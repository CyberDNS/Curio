.PHONY: help dev up down logs clean build migrate test test-backend test-frontend test-coverage clean-test

help:
	@echo "Curio - Available Commands:"
	@echo ""
	@echo "  make dev             - Start development environment"
	@echo "  make up              - Start production environment"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs"
	@echo "  make clean           - Clean up containers and volumes"
	@echo "  make build           - Build Docker images"
	@echo "  make migrate         - Run database migrations"
	@echo "  make test            - Run all tests"
	@echo "  make test-backend    - Run backend tests only"
	@echo "  make test-frontend   - Run frontend tests only"
	@echo "  make test-coverage   - Run tests with coverage"
	@echo "  make clean-test      - Clean test artifacts"
	@echo "  make backup          - Backup database"
	@echo "  make restore         - Restore database from backup"
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

test: test-backend test-frontend
	@echo "✅ All tests completed"

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest -v

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test -- --run

test-coverage:
	@echo "Running tests with coverage..."
	@echo "Backend coverage:"
	cd backend && pytest --cov=app --cov-report=term-missing --cov-report=html
	@echo "\nFrontend coverage:"
	cd frontend && npm run test:coverage
	@echo "\n📊 Coverage reports generated:"
	@echo "  Backend:  backend/htmlcov/index.html"
	@echo "  Frontend: frontend/coverage/index.html"

clean-test:
	@echo "Cleaning test artifacts..."
	rm -rf backend/htmlcov backend/.coverage backend/.pytest_cache backend/coverage.xml
	rm -rf frontend/coverage frontend/.vitest
	@echo "✅ Test artifacts cleaned"

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
