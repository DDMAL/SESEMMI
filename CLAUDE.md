# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SESEMMI** (Search Engine System for Enhancing Music Metadata Interoperability) is a Next.js full-stack app that translates natural language queries into SPARQL, executes them against a Virtuoso RDF triplestore containing 7 linked music databases (Cantus DB, DIAMM, MusicBrainz, RISM, etc.), and displays results in a table.

## Commands

```bash
# Next.js app
npm run dev           # Start dev server
npm run build         # Production build
npm run lint          # ESLint
npm run format        # Prettier (format in place)
npm run format:check  # Check formatting
npm run type-check    # TypeScript type check
npm run test          # Run all tests (single run)
npm run test:watch    # Watch mode

# Run a single test file
npx vitest run __tests__/lib/sparql/validate.test.ts

# Python llm-service (from llm-service/)
uv run uvicorn app.main:app --reload   # Dev server (port 8000)
uv run pytest                          # Run all Python tests

# Docker-based (preferred for integration)
make dev              # Start full dev stack (Next.js + Virtuoso + llm-service)
make test             # Run tests in Docker
make prod             # Start production stack
```

## Architecture

**Request flow:** User NL input → `POST /api/translate` (Next.js proxy) → Python llm-service → LangGraph pipeline → SPARQL editor (editable) → `POST /api/execute` (Virtuoso) → results table.

**Streaming flow:** `POST /api/translate/stream` proxies SSE from Python `/translate/stream`, emitting `step_start`, `step_done`, `token`, `done`, and `error` events as the LangGraph graph runs.

**Key Next.js directories:**
- `src/app/api/` — Four route handlers: `translate`, `translate/stream`, `execute`, `health`
- `src/components/` — UI: `NLInput`, `SparqlEditor`, `ResultsTable`, `Spinner`
- `src/hooks/` — `useTranslate`, `useExecuteSparql` (React Query mutations)
- `src/lib/llm/client.ts` — Thin HTTP client proxying to the Python llm-service (with 3-attempt retry)
- `src/lib/sparql/` — Lightweight regex validator + Virtuoso HTTP client
- `src/lib/` — `env.ts` (Zod env validation), `feature-flags.ts`, `rate-limit.ts`, `logger.ts`

**Python LLM microservice** (`llm-service/`):
- FastAPI service exposing `POST /translate`, `POST /translate/stream`, and `GET /health`
- Configured via `pydantic-settings` in `app/config.py`
- Package manager: `uv`; formatter: `black`; test runner: `pytest` with `asyncio_mode = auto`

**LangGraph pipeline** (`llm-service/app/graph/`):
- Nodes: `intake` → `retrieve` → `generate` → `validate` → `execute` → `answer`
- Conditional edges: after `validate`, loops back to `generate` on invalid SPARQL (up to `MAX_REPAIR_ITERATIONS`); after `answer`, semantic judge (`SEMANTIC_JUDGE_ENABLED`) can trigger a regeneration loop
- State is typed in `app/graph/state.py` (`GraphState` TypedDict)
- Graph tools: `sparql_execute` (runs query against Virtuoso), `wikidata` (resolves entity QIDs)
- `model.py` — LLM provider factory (`get_chat_model()`); `examples.py` — static few-shot examples; `schema_corpus.py` — per-database ontology chunks
- RAG via `langchain-postgres` (pgvector) — seeded on startup when `RAG_ENABLED=true`

**SPARQL validation** (`src/lib/sparql/validate.ts`):
- Lightweight regex-based pre-check (empty, missing SELECT/CONSTRUCT/ASK/DESCRIBE, unbalanced braces, missing WHERE)
- Not a full parser — defers complex syntax errors to Virtuoso response

**Rate limiting** (`src/lib/rate-limit.ts`):
- In-memory Map per IP; translate: 10 req/min, execute: 20 req/min

## Environment Variables

**Next.js** (validated at startup via Zod in `src/lib/env.ts`):

| Variable | Required | Default |
|---|---|---|
| `VIRTUOSO_ENDPOINT` | yes | — |
| `LLM_SERVICE_URL` | no | `http://llm:8000` |
| `LLM_API_KEY` | yes | — |
| `LOG_LEVEL` | no | `info` |

**Python llm-service** (via `pydantic-settings` in `app/config.py`):

| Variable | Default |
|---|---|
| `LLM_API_KEY` | required |
| `LLM_MODEL` | `gemini-2.5-flash-lite` |
| `EMBEDDING_MODEL` | `gemini-embedding-001` |
| `RAG_ENABLED` | `false` |
| `RAG_TOP_K` | `5` |
| `FEW_SHOT_ENABLED` | `false` |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@postgres:5432/sesemmi` |
| `VIRTUOSO_ENDPOINT` | `http://virtuoso:8890/sparql` |
| `MAX_REPAIR_ITERATIONS` | `3` |
| `SEMANTIC_JUDGE_ENABLED` | `true` |
| `SPARQL_TIMEOUT` | `120` (seconds) |
| `LANGSMITH_TRACING` | `false` |
| `LANGSMITH_API_KEY` | `None` |
| `LANGSMITH_PROJECT` | `sesemmi-agent` |

Copy `.env.example` to `.env.local` for local development.

## Key Conventions

- **Path alias**: `@/*` maps to `./src/*`
- **API error responses**: always use `apiError(message, status)` from `src/lib/api-error.ts`
- **Logging**: use the Pino logger from `src/lib/logger.ts` with structured `{ event, ...context }` fields
- **Input validation**: Zod schemas in `src/lib/validations/` must be parsed before use in route handlers
- **Client components**: mark with `"use client"` — hooks in `src/hooks/` are client-only
- **Tests**: located in `__tests__/` mirroring `src/lib/` structure; use Vitest
