# Testing Documentation

This document describes the testing infrastructure and how to run tests for the Curio application.

## Overview

Curio includes comprehensive test suites for both backend (Python/FastAPI) and frontend (TypeScript/React):

- **Backend**: pytest-based unit and integration tests
- **Frontend**: Vitest and React Testing Library tests
- **Coverage**: Both suites include code coverage reporting

## Backend Tests

### Setup

The backend uses pytest with the following dependencies:

- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `httpx` - HTTP client for testing
- `faker` - Test data generation

### Test Structure

```
backend/tests/
├── conftest.py              # Test fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_llm_processor.py    # LLM service tests
├── test_rss_fetcher.py      # RSS fetcher tests
├── test_api_articles.py     # Articles API tests
├── test_api_endpoints.py    # Other API endpoint tests
└── test_integration.py      # End-to-end integration tests
```

### Running Backend Tests

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::TestAuthentication::test_create_access_token

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Test Fixtures

Key fixtures available in `conftest.py`:

- `db_session` - SQLAlchemy database session (in-memory SQLite)
- `client` - FastAPI TestClient
- `authenticated_client` - Authenticated TestClient with auth cookie
- `test_user` - Sample User object
- `test_category` - Sample Category object
- `test_feed` - Sample Feed object
- `test_article` - Sample Article object
- `multiple_articles` - List of sample articles

### Coverage Report

After running tests with coverage, view the HTML report:

```bash
cd backend
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Frontend Tests

### Setup

The frontend uses Vitest with React Testing Library:

- `vitest` - Test framework (Vite-native)
- `@testing-library/react` - React component testing
- `@testing-library/jest-dom` - DOM matchers
- `@testing-library/user-event` - User interaction simulation
- `msw` - API mocking

### Test Structure

```
frontend/src/
├── test/
│   ├── setup.ts           # Test environment setup
│   ├── mockData.ts        # Mock data for tests
│   └── handlers.ts        # MSW API handlers
└── __tests__/
    ├── hooks/
    │   ├── useArticleActions.test.tsx
    │   └── useArticleFilters.test.tsx
    └── utils/
        └── api.test.ts
```

### Running Frontend Tests

```bash
# Run all tests
cd frontend
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run in watch mode (during development)
npm test -- --watch

# Run specific test file
npm test useArticleActions.test.tsx
```

### Writing Frontend Tests

Example component test:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MyComponent from "./MyComponent";

describe("MyComponent", () => {
  it("renders correctly", () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MyComponent />
      </QueryClientProvider>
    );

    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
```

## Integration Tests

The backend includes integration tests that cover complete workflows:

1. **Article Workflow**: Feed fetch → LLM processing → Reading
2. **Newspaper Generation**: Processed articles → Newspaper
3. **Duplicate Detection**: Similar articles → Deduplication
4. **User Isolation**: Multi-user data separation

Run integration tests specifically:

```bash
cd backend
pytest -m integration
```

## Continuous Integration

### GitHub Actions

Tests run automatically on:

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

The CI pipeline:

1. Sets up Python and Node.js environments
2. Installs dependencies
3. Runs backend tests with PostgreSQL
4. Runs frontend tests
5. Uploads coverage reports to Codecov
6. Runs linting checks

### Local CI Simulation

Run tests like CI does:

```bash
# Backend
cd backend
pytest --cov=app --cov-report=xml

# Frontend
cd frontend
npm test -- --run --coverage
```

## Makefile Targets

Use the Makefile for common test tasks:

```bash
# Run all tests
make test

# Run backend tests only
make test-backend

# Run frontend tests only
make test-frontend

# Run with coverage
make test-coverage

# Clean test artifacts
make clean-test
```

## Test Best Practices

### Backend

1. Use fixtures for common setup
2. Mock external services (OpenAI, HTTP requests)
3. Use in-memory database for speed
4. Test both success and error cases
5. Mark tests as `unit` or `integration`

### Frontend

1. Use React Testing Library's user-centric queries
2. Mock API calls with MSW
3. Test user interactions, not implementation details
4. Use `waitFor` for async operations
5. Keep tests isolated and independent

### General

- Write descriptive test names
- One assertion per test when possible
- Keep tests fast
- Maintain test data fixtures
- Update tests when changing code

## Troubleshooting

### Backend Tests Failing

**Database connection errors:**

```bash
# Make sure PostgreSQL is running (for integration tests)
docker-compose up -d postgres

# Or use SQLite (default for unit tests)
pytest  # Uses in-memory SQLite by default
```

**Import errors:**

```bash
# Install test dependencies
cd backend
pip install -r requirements.txt
```

### Frontend Tests Failing

**Module not found:**

```bash
# Install dependencies
cd frontend
npm install
```

**Timeout errors:**

```bash
# Increase timeout in vitest.config.ts
test: {
  testTimeout: 10000
}
```

## Code Coverage Goals

- **Backend**: Aim for 80%+ coverage
- **Frontend**: Aim for 70%+ coverage
- **Critical paths**: 90%+ coverage (auth, data processing)

View current coverage:

```bash
# Backend
cd backend
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run test:coverage
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Vitest documentation](https://vitest.dev/)
- [MSW (Mock Service Worker)](https://mswjs.io/)
