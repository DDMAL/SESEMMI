# LangGraph Agent Migration Plan for `llm-service/`

## Context

The current LLM service has two problems: (1) it uses a simple `prompt | model` chain with no validation, execution, self-repair, or dynamic QID resolution, and (2) the schema context is a monolithic 607-line string dumped into every prompt regardless of which databases are relevant.

The goal is to refactor into a LangGraph StateGraph agent with a schema-grounded retrieval-and-execution loop, **and** restructure the schema context into retrievable chunks so the agent gets only the smallest useful context for each query. The existing chain is kept as a fallback behind a feature flag.

---

## 1. State Schema

**New file: `app/graph/state.py`**

```python
class GraphState(TypedDict, total=False):
    # Inputs
    user_query: str

    # Intake
    intent: str                    # lookup | aggregation | comparison | path | cross_graph
    target_graphs: list[str]       # e.g. ["diamm", "musicbrainz"] — constrained to known DB names
    mentions_entities: bool        # True if query references named entities needing QID resolution
    needs_federation: bool         # True if query requires Wikidata SERVICE blocks

    # Retrieval
    schema_context: str            # ontology context (full or filtered)
    few_shot_examples: str         # formatted RAG/static examples
    resolved_qids: dict[str, str]  # {"Taylor Swift": "Q26876"}

    # Generation
    reasoning: str
    sparql: str

    # Validation
    validation_errors: list[str]
    is_valid: bool

    # Execution
    execution_error: str | None
    result_count: int
    results: dict | None

    # Semantic judge (answer node, optional)
    judge_feedback: str | None     # LLM judge's reason if results don't satisfy intent

    # Loop control
    repair_count: int              # starts at 0
    max_repairs: int               # from config (default 3)

    # Output
    confidence: str                # high | medium | low
    assumptions: list[str]
```

---

## 2. Graph Structure

```
START → [intake] → [retrieve] → [generate] → [validate]
                                     ^             |
                                     |        valid? ──yes──→ [execute]
                                     |             |               |
                                     |            no          success?
                                     |             |          /       \
                                     |             v        no        yes
                                     +────── [repair: re-enter    [answer]
                                              generate with       (+ judge)
                                              error context]     /        \
                                              (if count < max) judge:no   judge:yes
                                              else → [answer]    |          → END
                                                            (repairs left)
                                                            [generate]
```

**Nodes (6):**
1. `intake` — LLM classifies intent + target graphs + entity/federation flags (structured output with enum-constrained `target_graphs`)
2. `retrieve` — Deterministic routing (schema/instructions selected by intake output) + filtered RAG for examples + pre-emptive QID lookup
3. `generate` — Constrained SPARQL generation with Wikidata QID tool binding; on repair iterations, appends previous SPARQL + error
4. `validate` — rdflib `prepareQuery` syntax check + custom safety/prefix checks + rule-based structural intent checks (see §5)
5. `execute` — HTTP POST to Virtuoso, capture results or error
6. `answer` — Assemble final response with confidence/assumptions; optionally runs an LLM semantic judge (see §6a)

**Conditional routing:**
- After `validate`: valid → `execute`; invalid + repairs left → `generate`; else → `answer`
- After `execute`: success → `answer`; error + repairs left → `generate`; else → `answer`
- After `answer` (judge enabled): judge satisfied → END; judge unsatisfied + repairs left → `generate` with `judge_feedback`; else → END

---

## 3. Routed Schema Context & Filtered RAG

### Problem
The current `schema_context.py` is a 607-line monolithic string. Every prompt gets the full ontology for all 7 databases plus all global instructions, wasting tokens and diluting relevance.

### Why Not Similarity Search for Schema?
Ontology chunks (Turtle triples like `mb:Recording rdfs:label "label" ; wdt:P175 "performer"`) and meta-instructions ("don't use SERVICE inside GRAPH") have low embedding similarity to natural language user queries. Fixed-k similarity search is unreliable for this content and can't adapt to query complexity (a single-graph lookup needs 1 ontology chunk; a cross-database query needs 3+).

### Solution: Deterministic Routing + Filtered RAG

The `intake` node already classifies `target_graphs`, `mentions_entities`, and `needs_federation`. The `retrieve` node uses these structured signals to **deterministically select** schema context (no embeddings needed) and **filter** example retrieval (similarity search with metadata constraints).

#### A. Per-Database Ontology Chunks (7 documents) — Dict Lookup

**New file: `app/rag/schema_corpus.py`**

Store ontology chunks as a plain Python dict keyed by database name. No vector store, no embeddings — just dict lookups driven by `target_graphs` from intake.

```python
ONTOLOGY_CHUNKS: dict[str, str] = {
    "diamm": """\
Database: DIAMM
Graph IRI: <https://linkedmusic.ca/graphs/diamm/>
Prefix: diamm: <https://linkedmusic.ca/graphs/diamm/>

Description: Digital Image Archive of Medieval Music. Contains compositions,
sources (manuscripts), archives, persons (composers), and geographic entities.

Ontology:
diamm:Composition rdfs:label "label" ; wdt:P136 "genre" ; ...
diamm:Archive rdfs:label "label" ; wdt:P11550 "RISM siglum" ; ...

QID linking: diamm:City, diamm:Country, diamm:Region, diamm:Archive,
diamm:Person, diamm:Organization all have wdt:P2888 "exact match" for
Wikidata reconciliation.""",
    "musicbrainz": "...",
    "thesession": "...",
    "theglobaljukebox": "...",
    "digthat lick": "...",
    "rism": "...",
    "cantusdb": "...",
}
```

#### B. Instruction/Constraint Chunks (grouped by topic) — Rule-Based Selection

Store as a dict keyed by topic name. The retrieve node selects which instructions to include based on intake signals, not embedding similarity.

```python
INSTRUCTION_CHUNKS: dict[str, str] = {
    "named_graph_rules": "...",
    "output_format_rules": "...",
    "qid_resolution_rules": "...",
    "federated_query_rules": "...",
    "entity_type_rules": "...",
    "string_matching_rules": "...",
    "musicbrainz_specific": "...",
}
```

**Selection rules (in the `retrieve` node):**

| Condition (from intake) | Instructions included |
|------------------------|-----------------------|
| Always | `named_graph_rules`, `output_format_rules` |
| `mentions_entities` is True | `qid_resolution_rules`, `string_matching_rules` |
| `needs_federation` is True or `len(target_graphs) > 1` | `federated_query_rules` |
| Query filters by entity type | `entity_type_rules` |
| `"musicbrainz"` in `target_graphs` | `musicbrainz_specific` |

#### C. Example Retrieval — Similarity Search with Metadata Filters

Keep examples in the existing `sparql_examples` pgvector collection (similarity search works well here because `page_content` is natural language, same modality as user queries). Enrich metadata for filtering:

```python
Document(
    page_content=example["nl"],
    metadata={
        "sparql": example["sparql"],
        "databases": ["diamm"],           # which databases are queried
        "challenge_level": 1,             # 1-4 complexity
        "patterns": ["single_graph", "entity_lookup"],  # query patterns used
        "has_federation": False,
        "has_aggregation": False,
    }
)
```

**Filtered retrieval (in the `retrieve` node):**

```python
if len(target_graphs) == 1:
    # Prefer examples from the target database
    examples = store.similarity_search(
        query, k=5,
        filter={"databases": {"$contains": target_graphs[0]}}
    )
elif needs_federation or len(target_graphs) > 1:
    # Prefer federated/cross-database examples
    examples = store.similarity_search(
        query, k=5,
        filter={"has_federation": True}
    )
else:
    examples = store.similarity_search(query, k=5)
```

If a filtered search returns fewer than `k` results, fall back to unfiltered similarity search to fill the remaining slots.

### Retrieval Flow in the `retrieve` Node

```
intake output (intent, target_graphs, mentions_entities, needs_federation)
    │
    ├─→ Ontology: ONTOLOGY_CHUNKS[db] for each db in target_graphs
    │   → 1 DB? Load 1 chunk. 3 DBs? Load 3 chunks. Deterministic.
    │
    ├─→ Instructions: select from INSTRUCTION_CHUNKS by rule table above
    │   → Always: named_graph_rules + output_format_rules
    │   → Conditionally: qid, federation, entity_type, musicbrainz rules
    │
    ├─→ Examples: similarity_search with metadata filter (see above)
    │   → Returns top-k NL→SPARQL examples matching query + target pattern
    │
    └─→ Assemble: instructions + ontology + examples → minimal context
```

### Key reuse
- `app/rag/embeddings.py` — same `GoogleGenerativeAIEmbeddings` instance, reused for example retrieval
- `app/rag/store.py` — existing example store preserved, metadata enriched
- `app/rag/retrieve.py` — existing `retrieve_examples()` preserved for fallback chain

### What this eliminates
- No second pgvector collection (`schema_context`) needed
- No embedding cost for ontology/instruction chunks
- No `seed_schema_store()` startup step
- No `app/rag/schema_store.py` file

---

## 4. Wikidata QID Tool

**New file: `app/graph/tools/wikidata.py`**

- Implement `wikidata_qid_lookup(entity_name: str, language: str = "en") -> list[dict]` calling the Wikidata `wbsearchentities` API
- Register as a LangChain `@tool` for the LLM in the `generate` node (model uses `bind_tools`)
- Also callable as a plain function by the `retrieve` node for pre-emptive resolution
- User will provide their existing script during implementation; plan assumes `wbsearchentities` endpoint
- The generate node runs a tool-calling loop (max 3 tool calls) to handle QID resolution before producing final SPARQL — most queries need 0-2 lookups; the repair loop handles edge cases

---

## 5. Validation

**New file: `app/graph/validation.py`**

Two layers — syntax/safety checks (always run) and structural intent checks (rule-based, using `GraphState`).

### A. Syntax & Safety Checks

Uses `rdflib.plugins.sparql.prepareQuery` for full syntax validation, plus:
- Forbidden keywords: `INSERT`, `DELETE`, `DROP`, `CREATE`, `LOAD`, `CLEAR`
- Unknown prefixes (not in the ontology's known set)
- Unknown predicates (not in schema context)
- Missing `GRAPH` clause when targeting specific databases
- Missing `LIMIT` on broad exploratory queries (warning, not error)

### B. Structural Intent Checks

Rule-based checks driven by `intent` and other `GraphState` fields — no LLM call, sub-millisecond:

| Intent / Signal | Required structural property |
|---|---|
| `aggregation` | SPARQL must contain `COUNT`, `SUM`, `AVG`, or `GROUP BY` |
| `comparison` | Must have multiple SELECT variables or `ORDER BY` |
| `cross_graph` | Must reference ≥ 2 distinct graph IRIs from `target_graphs` |
| `mentions_entities=True` | Must contain at least one QID-shaped literal (`wd:Q\d+`) |
| `needs_federation=True` | Must contain a `SERVICE` block |

Violations are appended to `validation_errors` with the same repair feedback format as syntax errors. This catches the common failure mode where generated SPARQL is syntactically valid but structurally wrong for the query type (e.g., aggregation query with no `COUNT`).

---

## 6. Execution

**New file: `app/graph/tools/sparql_execute.py`**

- Async `execute_sparql(query: str, endpoint: str) -> dict` using `httpx.AsyncClient`
- POST with `application/x-www-form-urlencoded`, Accept `application/sparql-results+json`
- Returns parsed JSON results or error string
- Read-only mode (no update operations — enforced by validation node)

---

## 6a. Semantic Judge (Answer Node, Optional)

**Implemented inside `app/graph/nodes/answer.py`; gated by `settings.semantic_judge_enabled`.**

The structural intent checks in `validate` (§5B) catch obvious structural mismatches before execution. The semantic judge catches the subtler failure: syntactically and structurally valid SPARQL that returns plausible-looking results which nonetheless don't answer the user's intent.

**Why post-execution, not pre-execution:**
- Pre-execution LLM validation reasons blind (no results) — unreliable and adds cost to every query
- Post-execution reasoning is grounded in actual results — more accurate and only runs on successful executions
- Keeps syntax/safety validation deterministic and fast

**Judge prompt (condensed):**
```
User asked: {user_query}
Generated SPARQL: {sparql}
First 5 result rows: {results[:5]}

Do these results directly answer the user's question?
Reply: {"satisfied": true/false, "reason": "..."}
```

**Routing from `answer`:**
- `satisfied=true` → write `confidence`, `assumptions` → END
- `satisfied=false` + `repair_count < max_repairs` → write `judge_feedback` to state → re-enter `generate` with feedback as repair context
- `satisfied=false` + repairs exhausted → write `confidence="low"`, `assumptions` including judge's reason → END

**Repair message on judge failure:**
> "Results don't satisfy the query: {reason}. Reconsider the query structure — check predicates, filters, and GRAPH targeting against the ontology."

**Cost note:** One small LLM call (few tokens in, structured JSON out) per successful execution. Skip with `semantic_judge_enabled=false` in latency-sensitive deployments.

---

## 7. Self-Repair Loop

- `repair_count` starts at 0, incremented each time `generate` is re-entered after a failure
- `max_repairs` from `settings.max_repair_iterations` (default 3)
- Repair can be triggered by: `validate` (syntax/structural errors), `execute` (Virtuoso error or empty results), or `answer` (semantic judge failure)
- On re-entry, the generate node prepends: previous SPARQL, error messages, and targeted fix instructions:
  - Syntax error → "Fix the syntax error: {error}"
  - Structural intent mismatch → "Query structure doesn't match intent '{intent}': {error}"
  - Unknown prefix → "Use only these prefixes: {known}"
  - Forbidden clause → "Remove update operations"
  - Virtuoso error → "Query failed with: {error_text}"
  - Empty results → "Query returned 0 results. Verify: (1) QIDs are correct via wikidata_qid_lookup, (2) predicates exist in the target graph's ontology, (3) GRAPH IRI matches the target database. Do NOT remove valid constraints — fix the URIs instead."
  - Judge failure → "Results don't satisfy the query: {judge_feedback}. Reconsider the query structure."

---

## 8. LangSmith Observability

Integrate LangSmith for tracing and debugging the agent pipeline.

**Config additions in `app/config.py`:**
```python
langsmith_api_key: str | None = None
langsmith_project: str = "sesemmi-agent"
langsmith_tracing: bool = False
```

**Setup in `app/main.py` (lifespan):**
When `langsmith_tracing=True`, set the environment variables that LangSmith auto-detects:
```python
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
```

LangChain and LangGraph automatically emit traces when these env vars are set — no code changes needed in the nodes.

**Dependency:** Add `langsmith` to `pyproject.toml`.

**Docker env:** Add `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING` to docker-compose.

---

## 9. Config Changes

**Modified file: `app/config.py`**

Add:
```python
virtuoso_endpoint: str = "http://virtuoso:8890/sparql"
max_repair_iterations: int = 3
graph_enabled: bool = False         # feature flag for gradual rollout
semantic_judge_enabled: bool = False  # post-execution LLM result quality check
langsmith_api_key: str | None = None
langsmith_project: str = "sesemmi-agent"
langsmith_tracing: bool = False
```

---

## 10. API Changes

**Modified file: `app/main.py`**

- Branch on `settings.graph_enabled`: True → `run_graph(query)`, False → existing `translate_to_sparql(query)`
- Extend `TranslateResponse` with optional fields (backward-compatible):
  ```python
  graphs: list[str] | None = None
  confidence: str | None = None
  assumptions: list[str] | None = None
  resultCount: int | None = None
  executionError: str | None = None
  results: dict | None = None
  ```
- The Next.js frontend only reads `sparql`, so new fields are ignored until frontend is updated

---

## 11. File Plan

### New files
| File | Purpose |
|------|---------|
| `app/graph/__init__.py` | Package |
| `app/graph/state.py` | `GraphState` TypedDict |
| `app/graph/builder.py` | `build_graph()` + `run_graph()` entry point |
| `app/graph/nodes/__init__.py` | Package |
| `app/graph/nodes/intake.py` | Intent classification node |
| `app/graph/nodes/retrieve.py` | Deterministic routing (ontology/instruction dict lookup) + filtered RAG for examples + QID pre-resolution |
| `app/graph/nodes/generate.py` | Constrained SPARQL generation with tool-calling loop |
| `app/graph/nodes/validate.py` | rdflib syntax/safety checks + rule-based structural intent checks |
| `app/graph/nodes/execute.py` | Virtuoso execution |
| `app/graph/nodes/answer.py` | Response assembly + optional LLM semantic judge (gated by `semantic_judge_enabled`) |
| `app/graph/tools/__init__.py` | Package |
| `app/graph/tools/wikidata.py` | Wikidata QID lookup tool |
| `app/graph/tools/sparql_execute.py` | Async Virtuoso client |
| `app/graph/validation.py` | rdflib syntax/safety validation + structural intent check rules |
| `app/rag/schema_corpus.py` | `ONTOLOGY_CHUNKS` dict (per-database) + `INSTRUCTION_CHUNKS` dict (per-topic) — plain Python, no vector store |
| `tests/test_graph/test_validate.py` | Validation unit tests |
| `tests/test_graph/test_nodes.py` | Per-node unit tests |
| `tests/test_graph/test_integration.py` | End-to-end graph test (mocked LLM + Virtuoso) |

### Modified files
| File | Changes |
|------|---------|
| `app/config.py` | Add `virtuoso_endpoint`, `max_repair_iterations`, `graph_enabled`, `semantic_judge_enabled`, LangSmith settings |
| `app/main.py` | Feature-flag branch, extended response model, LangSmith setup |
| `app/rag/store.py` | Enrich example metadata (databases, challenge_level, patterns, has_federation, has_aggregation) |
| `pyproject.toml` | Add `langgraph`, `rdflib`, `httpx`, `langsmith` |

### Unchanged files (reused as-is)
| File | Reuse |
|------|-------|
| `app/llm/chain.py` | Fallback path; `clean_sparql()` imported by generate node |
| `app/llm/prompt.py` | `build_prompt_template()`, `format_examples()` imported by generate node |
| `app/llm/schema_context.py` | `SCHEMA_CONTEXT` used by fallback chain; decomposed into `schema_corpus.py` dicts for graph path |
| `app/llm/examples.py` | `FEW_SHOT_EXAMPLES` imported by retrieve node |
| `app/rag/retrieve.py` | `retrieve_examples()` called by retrieve node |
| All existing tests | Pass unchanged — they test the old chain path |

---

## 12. Implementation Sequence

### Phase 1 — Foundation
1. Add `langgraph`, `rdflib`, `httpx`, `langsmith` to `pyproject.toml`
2. Add new settings to `app/config.py`
3. Create `app/graph/state.py`
4. Create `app/graph/validation.py` (rdflib-based)
5. Create `app/graph/tools/wikidata.py` (placeholder using `wbsearchentities`; user provides real script)
6. Create `app/graph/tools/sparql_execute.py`
7. Write unit tests for validation and tools

### Phase 2 — Schema Context Restructuring
8. Create `app/rag/schema_corpus.py` — decompose `schema_context.py` into `ONTOLOGY_CHUNKS` dict (7 entries, keyed by DB name) + `INSTRUCTION_CHUNKS` dict (7 entries, keyed by topic)
9. Enrich example metadata in `app/rag/store.py` (databases, challenge_level, patterns, has_federation, has_aggregation)
10. Write tests for schema corpus completeness (all 7 DBs present, all instruction topics covered)

### Phase 3 — Nodes
11. Implement each node (`intake`, `retrieve`, `generate`, `validate`, `execute`, `answer`)
    - `intake` returns structured output with enum-constrained `target_graphs`, `mentions_entities`, `needs_federation`
    - `retrieve` node uses deterministic routing (ontology dict lookup by `target_graphs`, instruction selection by rule table) + filtered `similarity_search` for examples
    - `validate` node runs both syntax/safety checks (rdflib) and structural intent checks (rule table in §5B)
    - `answer` node runs optional LLM semantic judge when `semantic_judge_enabled=True`; adds conditional routing edge back to `generate` on judge failure
12. Write per-node unit tests with mocked LLM
    - validate: test each structural intent check rule independently
    - answer/judge: test satisfied vs. unsatisfied paths with mocked judge response

### Phase 4 — Graph assembly
13. Create `app/graph/builder.py` — wire nodes, edges, conditional routing
14. Write integration test (mock LLM + Virtuoso, test happy path + repair loop)

### Phase 5 — API integration
15. Extend `TranslateResponse` in `app/main.py`
16. Add feature-flag branch in `/translate` handler
17. Verify all existing tests still pass

### Phase 6 — Deployment
18. Update docker-compose env with `VIRTUOSO_ENDPOINT`, `GRAPH_ENABLED`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING`
19. Update `CLAUDE.md` with new architecture

---

## 13. Verification

1. **Unit tests**: `uv run pytest tests/test_graph/` — all validation, tool, and node tests pass
2. **Existing tests**: `uv run pytest` — all 14 existing tests still pass (chain fallback path)
3. **Integration test**: Mock LLM returns a known SPARQL query, mock Virtuoso returns results; verify the full graph executes and returns expected response shape
4. **Repair loop test**: Mock LLM to produce invalid SPARQL on first attempt, valid on second; verify `repair_count` increments and the graph self-corrects
5. **Structural intent check test**: Mock `intake` to return `intent="aggregation"`; mock `generate` to produce valid SPARQL with no `COUNT`; verify `validate` catches it and triggers repair
6. **Semantic judge test**: Mock judge to return `satisfied=false`; verify repair re-enters `generate` with `judge_feedback`; verify exhausted repairs set `confidence="low"`
5. **Feature flag**: With `GRAPH_ENABLED=false`, verify `/translate` uses the old chain path
6. **Manual E2E**: `GRAPH_ENABLED=true make dev`, send a query via the UI, verify SPARQL + results return
