# Curio - AI News Aggregator

## Architecture Overview

FastAPI + React news aggregator with AI curation pipeline:
RSS Fetcher → LLM Processor (parallel) → Duplicate Detector → Newspaper Generator → Scheduler

**Critical**: Articles have two titles: `article.title` (original) and `article.llm_title` (AI-enhanced). Always use `llm_title` for display when available.

## Authentication & Security

**OAuth + Dev Mode**: Production uses OAuth (Google/Microsoft). Dev: `DEV_MODE=true` bypasses auth.

- Tokens: HttpOnly cookies (`auth_token`) + JWT
- Always use: `current_user: User = Depends(get_current_user)`
- **CRITICAL**: ALL queries MUST filter by `user_id` (multi-tenancy)

```python
# ✅ Correct
articles = db.query(Article).filter(Article.user_id == current_user.id).all()
```

## LLM Processing

**Parallel with Rate Limiting** (`backend/app/services/llm_processor.py`):

- Uses token bucket rate limiter + semaphore (default: 5 concurrent)
- Config: `LLM_MAX_CONCURRENT=5`, `LLM_TPM_LIMIT=90000`, `LLM_MAX_INPUT_TOKENS=2000`
- Content truncated & images stripped before LLM
- Always use rate limiter: `await self.rate_limiter.acquire(estimated_tokens)`

## Testing

**Backend**: `pytest -v` (use fixtures: `db_session`, `authenticated_client`, `mock_openai_response`)
**Frontend**: `npm test` (MSW handlers in `frontend/src/test/handlers.ts`)

## Common Tasks

**Add Endpoint**: Create in `api/endpoints/` → Add `@limiter.limit("30/minute")` → Add auth → Filter by `user_id` → Register in `main.py`

**Migration**: `cd backend && alembic revision --autogenerate -m "desc" && alembic upgrade head`

**Trigger Jobs**: `POST /api/actions/run-full-update`

## Critical Rules

- **DO NOT create .md documentation files automatically** - Only when user explicitly requests
- Always filter by `user_id` in queries (security)
- Use rate limiter for all LLM calls (TPM limits)
- Use `withCredentials: true` for API calls (auth cookies)
- Keep system prompts under 250 tokens

## Key Files

- LLM: `backend/app/services/llm_processor.py`
- Auth: `backend/app/core/auth.py`
- Models: `backend/app/models/article.py`
- Config: `backend/app/core/config.py`
