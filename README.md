# inbox-guard

Email reply tracker for founders and managers. Connects a Gmail inbox, decides which
threads need a reply and how urgent they are, tracks unanswered threads, and alerts
on Telegram.

This is the working name; the Python package is `app`.

## Prerequisites

- Python 3.12
- Docker with Compose
- A virtualenv is recommended

Postgres is published on host port **5434** so it does not collide with other
local Postgres instances. Inside the container the server still listens on 5432.

## Setup

```bash
cp .env.example .env
docker compose up -d
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

Generate a Fernet key for `TOKEN_ENCRYPTION_KEY` when you start storing OAuth tokens:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health` → `{"status":"ok"}` (requires Postgres).

## Classifier CLI

Classify a JSON list of `{from, subject, body, headers, label?}` objects. Provider
settings come from the environment only. Email bodies are never printed.

```bash
python -m app.pipeline.classifier tests/fixtures/sample_emails.json
python -m app.pipeline.classifier emails.json --limit 20
```

`LLM_MODEL` is required. Tests use a fake provider and do not need an API key.

## Pointing the LLM at a provider

Set `LLM_PROVIDER`, `LLM_KEY`, `LLM_MODEL`, and (for OpenAI-compatible APIs)
`LLM_BASE_URL`. Optional: `LLM_JSON_MODE`, `LLM_PRICE_INPUT_PER_M`,
`LLM_PRICE_OUTPUT_PER_M`.

| Service    | `LLM_PROVIDER`       | `LLM_BASE_URL`                                              | Notes |
|------------|----------------------|---------------------------------------------------------------|--------|
| OpenAI     | `openai_compatible`  | `https://api.openai.com/v1`                                   | Default base URL |
| Groq       | `openai_compatible`  | `https://api.groq.com/openai/v1`                              | |
| OpenRouter | `openai_compatible`  | `https://openrouter.ai/api/v1`                                | |
| Gemini     | `openai_compatible`  | `https://generativelanguage.googleapis.com/v1beta/openai/`    | |
| Ollama     | `openai_compatible`  | `http://localhost:11434/v1`                                   | `LLM_KEY` can be any string or empty |
| Anthropic  | `anthropic`          | unused                                                        | Native Messages API; `LLM_BASE_URL` is ignored |

Examples:

```bash
# OpenAI
LLM_PROVIDER=openai_compatible
LLM_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Groq
LLM_PROVIDER=openai_compatible
LLM_KEY=gsk_...
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1

# OpenRouter
LLM_PROVIDER=openai_compatible
LLM_KEY=sk-or-...
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1

# Gemini (OpenAI-compatible endpoint)
LLM_PROVIDER=openai_compatible
LLM_KEY=...
LLM_MODEL=gemini-2.0-flash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Ollama (local; no real key required)
LLM_PROVIDER=openai_compatible
LLM_KEY=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://localhost:11434/v1
LLM_JSON_MODE=false

# Anthropic
LLM_PROVIDER=anthropic
LLM_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5
```

Set `LLM_JSON_MODE=false` if the provider rejects `response_format={"type":"json_object"}`.

## Tests and lint

Tests use a separate `inboxguard_test` database (created by `docker/init-db.sql`).
Postgres must be running. Classifier tests do not call the network.

```bash
docker compose up -d
pytest
ruff check .
```

Optional type check:

```bash
mypy
```

## Project layout (current)

```
app/
  main.py          FastAPI app, /health
  config.py        settings from env
  db/              SQLAlchemy models, session, Alembic migrations
  providers/       LLMProvider protocol, OpenAI-compatible + Anthropic
  pipeline/        rules filter, body cleaning, scoring, classifier CLI
tests/
  fixtures/sample_emails.json
docker-compose.yml
.env.example
```
