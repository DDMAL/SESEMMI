# CLAUDE.md

## Project overview

**SESEMMI** (Search Engine System for Enhancing Music Metadata Interoperability) is a Next.js full-stack app that translates natural-language queries into SPARQL, runs them against a Virtuoso triplestore holding 14 linked music databases (Cantus DB, DIAMM, MusicBrainz, RISM, three NFDI4Culture CKG feeds, …), and shows the results in a table.

## Commands

```bash
# Next.js app
npm run dev           # Dev server
npm run build         # Production build
npm run lint          # ESLint
npm run format        # Prettier (write); format:check to verify only
npm run type-check    # TypeScript
npm run test          # Vitest, single run; test:watch for watch mode
npx vitest run __tests__/lib/sparql/validate.test.ts   # One test file

# Python llm-service (run from llm-service/)
uv run uvicorn app.main:app --reload   # Dev server (port 8000)
uv run pytest                          # All Python tests

# Docker (preferred for integration)
make dev     # Dev stack: Next.js + llm-service + postgres + ollama (Virtuoso is remote/prod)
make test    # Tests in Docker
make prod    # Production stack
```

## Architecture

**Request flow:** NL input → `POST /api/translate` (Next.js proxy) → Python llm-service → LangGraph pipeline → editable SPARQL editor → `POST /api/execute` (Virtuoso) → results table. The streaming variant (`POST /api/translate/stream`) proxies SSE from the Python `/translate/stream`, emitting `step_start`/`step_done`/`token`/`done`/`error` as the graph runs.

**Next.js** (`src/`): route handlers in `app/api/` (`translate`, `translate/stream`, `execute`, `health`); `lib/llm/client.ts` proxies to the Python service with a 3-attempt retry; `lib/sparql/` holds the regex validator + Virtuoso client; `lib/env.ts` validates env with Zod. Path alias `@/*` → `./src/*`.

**Python llm-service** (`llm-service/`): FastAPI (`POST /translate`, `/translate/stream`, `GET /health`), configured by `pydantic-settings` in `app/config.py`. Package manager `uv`, formatter `black`, tests `pytest` (`asyncio_mode = auto`).

**LangGraph pipeline** (`app/graph/`, wired in `builder.py`):

- Nodes: `intake` → `retrieve` → `generate` → `validate` → `execute` → `judge`.
- Edges: after `validate` → `execute` | back to `generate` (invalid SPARQL) | `END`, bounded by `MAX_REPAIR_ITERATIONS`; after `judge` → back to `intake` (full repair round, when `judge_feedback` is set) | `END`.
- Node roles: `intake` classifies intent + target graphs (Qwen sometimes emits malformed structured output → it logs and falls back to broad graphs); `retrieve` assembles schema context + few-shot; `generate` writes SPARQL; `validate` is a regex pre-check, not a full parser (real syntax errors defer to Virtuoso); `execute` runs the query; `judge` scores confidence and, with `EMPTY_PROBE_ENABLED`, isolates which clause returned 0 rows (`tools/empty_probe.py`).
- Schema and instructions live **in code**, not in RAG: `schema_corpus.py` (`ONTOLOGY_CHUNKS` + `INSTRUCTION_CHUNKS`, one per database), `examples.py` (`FEW_SHOT_EXAMPLES`), `model.py` (provider factory: `get_chat_model()` / `get_structured_model()`), `ontology_parser.py` (shapes the schema slice). State is the `GraphState` TypedDict in `state.py`. RAG (pgvector) applies only when `RAG_ENABLED=true`; otherwise `retrieve` uses the static corpus, plus all of `FEW_SHOT_EXAMPLES` when `FEW_SHOT_ENABLED`.

**Rate limiting** (`src/lib/rate-limit.ts`): in-memory per IP — translate 10/min, execute 20/min.

## Environment variables

**Next.js** (Zod-validated at startup in `src/lib/env.ts`):

| Variable | Required | Default |
|---|---|---|
| `VIRTUOSO_ENDPOINT` | yes | — |
| `LLM_SERVICE_URL` | no | `http://llm:8000` |
| `LLM_API_KEY` | yes | — |
| `LOG_LEVEL` | no | `info` |

**Python llm-service** (`pydantic-settings` in `app/config.py`; reads the **root `.env`**, OS env overrides it — the Next.js app uses `.env.local`). Bold marks where the prod value differs from the default:

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `openai` \| `anthropic` \| `gemini` \| `qwen` |
| `LLM_MODEL` | `qwen3:1.7b` | **prod `qwen3.6-27b`** (via the `qwen` provider) |
| `QWEN_BASE_URL` | Aliyun MaaS `…/compatible-mode/v1` | OpenAI-compatible endpoint for the `qwen` provider |
| `DASHSCOPE_API_KEY` | — | auth for the `qwen`/DashScope endpoint (prod uses this) |
| `OPENAI_/ANTHROPIC_/GEMINI_API_KEY` | — | only the active provider's key is read |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | local ollama has only `qwen3:1.7b` + `nomic-embed-text` |
| `EMBEDDING_MODEL` | `nomic-embed-text` | RAG only |
| `RAG_ENABLED` | `false` | **prod `true`** (pgvector top-k example selection) |
| `RAG_TOP_K` | `5` | |
| `FEW_SHOT_ENABLED` | `false` | when RAG is off, gates the full static `FEW_SHOT_EXAMPLES` |
| `DATABASE_URL` | `postgresql+psycopg://…@postgres:5432/sesemmi` | pgvector store (RAG only) |
| `VIRTUOSO_ENDPOINT` | `http://virtuoso:8890/sparql` | **prod `https://virtuoso.simssa.ca/sparql`** |
| `MAX_REPAIR_ITERATIONS` | `3` | |
| `SEMANTIC_JUDGE_ENABLED` | `true` | |
| `EMPTY_PROBE_ENABLED` | `true` | zero-row clause isolation |
| `CLARIFICATION_ENABLED` | `true` | pre-translation disambiguation (`/clarify`) |
| `SPARQL_TIMEOUT` / `LLM_REQUEST_TIMEOUT` | `120` | seconds |
| `LANGSMITH_TRACING` | `false` | **prod `true`** |
| `LANGSMITH_API_KEY` | `None` | in root `.env` |
| `LANGSMITH_PROJECT` | `sesemmi-agent` | **prod logs to `sesemmi-prod`** |

## Working on queries & debugging

**Every real model call costs money — get user approval before each one, and test one query at a time.** Prod runs `qwen3.6-27b` over an Aliyun MaaS / DashScope OpenAI-compatible endpoint (the `qwen` provider; `QWEN_BASE_URL` + `DASHSCOPE_API_KEY` are in the root `.env`; in LangSmith these appear as `ChatOpenAI` calls). There is no local GPU — the `sesemmi-ollama` container only has `qwen3:1.7b`, which is **not** representative of prod, so never judge query quality from it. (`eval/` is stale — not a current benchmark or regression gate.)

**Validate SPARQL against prod Virtuoso first — free, no LLM.** Before spending a model call, confirm the shape returns rows / the predicate exists:

```bash
curl -s -G https://virtuoso.simssa.ca/sparql \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?n) WHERE { GRAPH <https://linkedmusic.ca/graphs/ckg-musiconn/> { ?e a <https://linkedmusic.ca/graphs/ckg-musiconn/Event> } }' \
  --data-urlencode 'format=application/sparql-results+json'
```

Named graphs are `https://linkedmusic.ca/graphs/<name>/` for: musicbrainz, rism, ckg-musiconn, ckg-detmold, ckg-apsearch, theglobaljukebox, thesession, diamm, cantusdb, cantusindex, dig-that-lick, simssadb, utsi, wjazzd. Prefer flat `UNION` shapes — Virtuoso rejects queries whose **estimated** cost exceeds its limit (correlated `OPTIONAL` subqueries over a derived key blow up). The HTTP endpoint needs no `SPARQL` prefix; ISQL does.

**Run one faithful query through the real pipeline (host-side).** The `sesemmi-llm` container fails startup locally (can't resolve host `postgres`), so `localhost:8000` is unreliable — drive the graph from the host venv instead:

```python
# from llm-service/, run with an absolute PYTHONPATH (see command below)
import asyncio, os
os.environ.update(LLM_PROVIDER="qwen", RAG_ENABLED="false",
                  FEW_SHOT_ENABLED="true", LANGSMITH_TRACING="false")
from app.graph.builder import run_graph  # -> {sparql, resultCount, executionError, results, graphs, ...}
print(asyncio.run(run_graph("your natural-language query")))
```

Run from `llm-service/` with `PYTHONPATH="$PWD" .venv/bin/python <script>.py` (a relative `PYTHONPATH` won't resolve `app`); the root `.env` supplies the model, endpoint, and prod Virtuoso. Caveat: this loads the *full static* `FEW_SHOT_EXAMPLES` rather than prod's RAG top-k (RAG needs pgvector + ollama embeddings, not up locally) — faithful on model and schema, less so on example selection. An `intake` structured-output parse error → broad-graph fallback matches prod and is harmless.

**LangSmith traces are the primary debugging signal.** The CLI is **`langsmith-cli`** (a uv tool — `uv tool list`), not `langsmith`, and uses the `runs` group. Projects: `sesemmi-prod` (deployed/demo runs — start here), `sesemmi-agent` (dev), `sesemmi-eval` (eval). Add `--api-key $LANGSMITH_API_KEY` (from `.env`):

```bash
langsmith-cli runs list --project sesemmi-prod --roots --limit 20 --json   # recent traces; root input = .inputs.user_query
langsmith-cli runs list --project sesemmi-prod --trace <id> --json          # full tree
```

Key nodes in a trace: `generate` (`.outputs.sparql`), `execute` (`.outputs.result_count` / `.results` / `.execution_error`), `judge`, `intake`, `retrieve`.

**Data facts that shape query design** (verified 2026-07-15):

- CKG feeds (ckg-musiconn / ckg-detmold / ckg-apsearch) carry **only `wdt:P2888` (Wikidata QID)** as a cross-database identifier — GND/VIAF from reconciliation are not kept in the RDF. A same-entity CKG↔other-DB join must bridge on the QID; the only non-Wikidata bridge is a shared literal (e.g. decade). Person-QID overlaps: musiconn∩musicbrainz 3195, rism∩musiconn 2282, detmold∩musicbrainz 207.
- The Detmold Hoftheater catalogue is mostly spoken **plays**, not operas.
- Frontend "starter" queries live in `src/lib/i18n/locales/*.ts` under `conversation.starters`, translated across en/de/es/fa/fr — **change all five together**. `#2` (Clara Schumann) is a known-good template.
- The recent schema-corruption fix, starter rework, ontology parser, and empty-probe landed in PR #34 (merged).

## Deploy

- `.github/workflows/build-push-deploy.yml`: **any push to `main` auto-deploys** — builds `sesemmi-app` + `sesemmi-llm` images to GHCR, then `kubectl set image` + rollout on `deployment/{app,llm}` in the `sesemmi` namespace. Branch pushes build images but do **not** deploy. CI (lint, type-check, tests) runs on every push.
- When creating a fix branch, **set upstream explicitly** (`git push -u origin <branch>`) — a branch left tracking `origin/main` pushes straight to main.
- No committed `node_modules`: run `npm ci` before a local `npm run type-check`, or rely on CI.

## Key conventions

- API error responses: use `apiError(message, status)` from `src/lib/api-error.ts`.
- Logging: the Pino logger from `src/lib/logger.ts`, with structured `{ event, ...context }` fields.
- Input validation: parse the Zod schemas in `src/lib/validations/` before use in route handlers.
- Client components: mark `"use client"`; hooks in `src/hooks/` are client-only.
- Tests: in `__tests__/`, mirroring `src/lib/`, using Vitest.
