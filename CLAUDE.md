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

**Request flow:** User NL input → `POST /api/translate` (LLM) → SPARQL editor (editable) → `POST /api/execute` (Virtuoso) → results table.

**Key directories:**
- `src/app/api/` — Three route handlers: `translate`, `execute`, `health`
- `src/components/` — UI: `NLInput`, `SparqlEditor`, `ResultsTable`, `Spinner`
- `src/hooks/` — `useTranslate`, `useExecuteSparql` (React Query mutations)
- `src/lib/llm/` — Google Gemini client, system prompt, 19 few-shot examples, schema context
- `src/lib/sparql/` — Lightweight regex validator + Virtuoso HTTP client
- `src/lib/` — `env.ts` (Zod env validation), `feature-flags.ts`, `rate-limit.ts`, `logger.ts`

**Python LLM microservice** (`llm-service/`):
- FastAPI service exposing `POST /translate` → `{ sparql, usage, durationMs }` and `GET /health`
- Configured via `pydantic-settings` in `app/config.py` (env vars: `LLM_API_KEY`, `LLM_MODEL`, `DATABASE_URL`, `RAG_ENABLED`, `RAG_TOP_K`, `FEW_SHOT_ENABLED`)
- Uses `langchain-google-genai` with `gemini-2.5-flash-lite` (same model as Next.js app)
- RAG via `langchain-postgres` (pgvector) — seeded from `app/rag/corpus.py` on startup when `RAG_ENABLED=true`
- Package manager: `uv`; formatter: `black`; test runner: `pytest` with `asyncio_mode = auto`
- Migration in progress (see `LANGGRAPH_MIGRATION_PLAN.md`): replacing simple `prompt | model` chain with a LangGraph `StateGraph` pipeline (graph routing → RAG retrieval → generate → validate/repair loop)

**Next.js LLM integration** (`src/lib/llm/`):
- Model: `gemini-2.5-flash-lite` via `@ai-sdk/google`
- `prompt.ts` builds the system prompt embedding schema context + few-shot examples
- `schema-context.ts` contains all graph IRIs, prefixes, and ontology rules for the 7 databases
- `examples.ts` contains 24 SPARQL examples covering single-graph, aggregation, federated, and cross-database queries
- Prompt instructs the model to output raw SPARQL only (no markdown fences)
- Feature flag `FEATURE_RAG_ENABLED` enables dynamic example selection (Phase 3)

**SPARQL validation** (`src/lib/sparql/validate.ts`):
- Lightweight regex-based pre-check (empty, missing SELECT/CONSTRUCT/ASK/DESCRIBE, unbalanced braces, missing WHERE)
- Not a full parser—defers complex syntax errors to Virtuoso response

**Rate limiting** (`src/lib/rate-limit.ts`):
- In-memory Map per IP; translate: 10 req/min, execute: 20 req/min

## Environment Variables

Validated at startup via Zod in `src/lib/env.ts`:

| Variable | Required | Default |
|---|---|---|
| `VIRTUOSO_ENDPOINT` | yes | — |
| `LLM_API_KEY` | yes | — |
| `LLM_MODEL` | no | `gemini-2.5-flash-lite` |
| `LOG_LEVEL` | no | `info` |
| `FEATURE_RAG_ENABLED` | no | `false` |

Copy `.env.example` to `.env.local` for local development.

## Key Conventions

- **Path alias**: `@/*` maps to `./src/*`
- **API error responses**: always use `apiError(message, status)` from `src/lib/api-error.ts`
- **Logging**: use the Pino logger from `src/lib/logger.ts` with structured `{ event, ...context }` fields
- **Input validation**: Zod schemas in `src/lib/validations/` must be parsed before use in route handlers
- **Client components**: mark with `"use client"` — hooks in `src/hooks/` are client-only
- **Tests**: located in `__tests__/` mirroring `src/lib/` structure; use Vitest
