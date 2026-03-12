# LangGraph Migration Implementation Plan

## Context

The `llm-service/` currently uses a simple `prompt | model` LangChain chain with no validation, execution, self-repair, or dynamic schema routing. The 607-line `schema_context.py` dumps the full ontology for all 7 databases into every prompt. This migration adds a LangGraph StateGraph agent with intake classification, deterministic schema routing, filtered RAG, Wikidata QID resolution, rdflib validation, Virtuoso execution, and a self-repair loop — all behind a `GRAPH_ENABLED` feature flag preserving backward compatibility.

---

## Step 1: Add Dependencies

**File:** `llm-service/pyproject.toml`

Add to `dependencies`:
- `langgraph>=0.2.0`
- `rdflib>=7.0.0`
- `langsmith>=0.1.0`

Move `httpx>=0.28.1` from `[dependency-groups] dev` to `dependencies` (needed at runtime by execute node).

**Verify:** `cd llm-service && uv lock && uv sync`

---

## Step 2: Extend Settings

**File:** `llm-service/app/config.py`

Add 7 fields to `Settings`:
```python
virtuoso_endpoint: str = "http://virtuoso:8890/sparql"
max_repair_iterations: int = 3
graph_enabled: bool = False
semantic_judge_enabled: bool = False  # post-execution LLM result quality check
langsmith_api_key: str | None = None
langsmith_project: str = "sesemmi-agent"
langsmith_tracing: bool = False
```

**Verify:** `uv run pytest` — all 14 existing tests pass (all fields have defaults).

---

## Step 3: Create GraphState

**New files:**
- `llm-service/app/graph/__init__.py` (empty)
- `llm-service/app/graph/state.py`

Define `GraphState(TypedDict, total=False)` with all 22 keys from section 1 of `LANGGRAPH_MIGRATION_PLAN.md`:

```python
class GraphState(TypedDict, total=False):
    # Inputs
    user_query: str

    # Intake
    intent: str                    # lookup | aggregation | comparison | path | cross_graph
    target_graphs: list[str]       # e.g. ["diamm", "musicbrainz"]
    mentions_entities: bool
    needs_federation: bool

    # Retrieval
    schema_context: str
    few_shot_examples: str
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
    repair_count: int
    max_repairs: int

    # Output
    confidence: str                # high | medium | low
    assumptions: list[str]
```

---

## Step 4: Create Validation Module

**New file:** `llm-service/app/graph/validation.py`

Two exported functions:

**`validate_sparql(sparql: str, target_graphs: list[str] | None = None) -> list[str]`** — syntax & safety checks:
1. Forbidden keyword check (INSERT, DELETE, DROP, CREATE, LOAD, CLEAR)
2. `rdflib.plugins.sparql.prepareQuery()` syntax check with `initNs` for all known prefixes
3. Unknown prefix detection
4. Missing GRAPH clause warning (when `target_graphs` provided)
5. Missing LIMIT warning for SELECT queries

**`validate_intent(sparql: str, intent: str, mentions_entities: bool, needs_federation: bool) -> list[str]`** — structural intent checks (rule-based, no LLM):

| Intent / Signal | Required structural property |
|---|---|
| `aggregation` | Must contain `COUNT`, `SUM`, `AVG`, or `GROUP BY` |
| `comparison` | Must have multiple SELECT variables or `ORDER BY` |
| `cross_graph` | Must reference ≥ 2 distinct graph IRIs |
| `mentions_entities=True` | Must contain at least one `wd:Q\d+` literal |
| `needs_federation=True` | Must contain a `SERVICE` block |

Violations use the same `list[str]` format as syntax errors and are merged into `validation_errors`.

Also: `is_valid(errors)` helper, `KNOWN_PREFIXES` dict.

**Known prefixes** (from `schema_context.py` lines 61-70):
```python
KNOWN_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "wd": "http://www.wikidata.org/entity/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "diamm": "https://linkedmusic.ca/graphs/diamm/",
    "ts": "https://linkedmusic.ca/graphs/thesession/",
    "mb": "https://linkedmusic.ca/graphs/musicbrainz/",
    "gj": "https://linkedmusic.ca/graphs/theglobaljukebox/",
    "dtl": "https://linkedmusic.ca/graphs/dig-that-lick/",
    "cdb": "https://linkedmusic.ca/graphs/cantusdb/",
    "rism": "https://linkedmusic.ca/graphs/rism/",
}
```

---

## Step 5: Validation Unit Tests

**New files:**
- `llm-service/tests/test_graph/__init__.py` (empty)
- `llm-service/tests/test_graph/test_validate.py`

**Syntax & safety tests (8):**
1. `test_valid_select_query` — correct SELECT with GRAPH and LIMIT returns empty errors
2. `test_forbidden_insert` — query with INSERT DATA returns error
3. `test_syntax_error_unbalanced_braces` — malformed query fails rdflib parsing
4. `test_unknown_prefix` — unrecognized prefix flagged
5. `test_missing_graph_clause` — query without GRAPH when target_graphs provided yields warning
6. `test_missing_limit_warning` — SELECT without LIMIT gets warning
7. `test_is_valid_with_only_warnings` — warnings don't block validity
8. `test_is_valid_with_errors` — real errors block validity

**Structural intent tests (5):**
9. `test_aggregation_missing_count` — `intent="aggregation"` + SPARQL with no COUNT/GROUP BY → error
10. `test_aggregation_valid` — `intent="aggregation"` + SPARQL with COUNT → no error
11. `test_cross_graph_single_graph` — `intent="cross_graph"` + SPARQL targeting only 1 graph → error
12. `test_mentions_entities_no_qid` — `mentions_entities=True` + SPARQL with no `wd:Q\d+` → error
13. `test_needs_federation_no_service` — `needs_federation=True` + SPARQL without SERVICE → error

**Verify:** `uv run pytest tests/test_graph/test_validate.py -v`

---

## Step 6: Wikidata QID Lookup Tool

**New files:**
- `llm-service/app/graph/tools/__init__.py` (empty)
- `llm-service/app/graph/tools/wikidata.py`

```python
@tool
async def wikidata_qid_lookup(entity_name: str, language: str = "en") -> list[dict]:
    """Look up a Wikidata entity QID by name. Returns top 5 matches."""
```

- Calls `https://www.wikidata.org/w/api.php` with `action=wbsearchentities`
- Uses `httpx.AsyncClient` with 10s timeout
- Returns `[{"qid": "Q26876", "label": "Taylor Swift", "description": "..."}]`
- Fail-open: returns `[]` on network errors
- Decorated with `@tool` from `langchain_core.tools` for LLM binding

---

## Step 7: Async Virtuoso Execution Tool

**New file:** `llm-service/app/graph/tools/sparql_execute.py`

```python
async def execute_sparql(query: str, endpoint: str | None = None) -> dict:
```

- POSTs to Virtuoso with `Content-Type: application/x-www-form-urlencoded`, `Accept: application/sparql-results+json`
- Uses `httpx.AsyncClient` with 30s timeout
- Returns `{"results": parsed_json, "error": None}` on success
- Returns `{"results": None, "error": error_text}` on failure
- Default endpoint from `settings.virtuoso_endpoint`

---

## Step 8: Decompose Schema Context into Corpus

**New file:** `llm-service/app/rag/schema_corpus.py`

Two dicts carved from `llm-service/app/llm/schema_context.py`:

### `ONTOLOGY_CHUNKS` (7 entries)

Keyed by DB name, each containing graph IRI, prefix, description, and Turtle ontology:

| Key | Source lines in schema_context.py | Graph IRI |
|-----|----------------------------------|-----------|
| `"diamm"` | 72-136 | `<https://linkedmusic.ca/graphs/diamm/>` |
| `"thesession"` | 138-169 | `<https://linkedmusic.ca/graphs/thesession/>` |
| `"musicbrainz"` | 171-470 | `<https://linkedmusic.ca/graphs/musicbrainz/>` |
| `"theglobaljukebox"` | 472-517 | `<https://linkedmusic.ca/graphs/theglobaljukebox/>` |
| `"digthat lick"` | 519-529 | `<https://linkedmusic.ca/graphs/dig-that-lick/>` |
| `"cantusdb"` | 531-540 | `<https://linkedmusic.ca/graphs/cantusdb/>` |
| `"rism"` | 542-604 | `<https://linkedmusic.ca/graphs/rism/>` |

Each chunk also includes its DB description (from lines 46-52) and prefix declaration.

### `INSTRUCTION_CHUNKS` (7 entries)

Extracted from the prose instructions in lines 1-43:

| Key | Content source |
|-----|---------------|
| `"named_graph_rules"` | Line 34: use `SELECT { GRAPH ... { } }` syntax, not `FROM` |
| `"output_format_rules"` | Lines 15-16: return labels+URIs, use rdf:type, add LIMIT |
| `"qid_resolution_rules"` | Lines 9-13, 17, 26-29: QID search workflow, wdt:P2888 linking, navigate to class for QID |
| `"federated_query_rules"` | Lines 22-25, 35-40: SERVICE placement outside GRAPH/OPTIONAL, subquery before SERVICE for SP031 |
| `"entity_type_rules"` | Lines 19-21: use rdf:type for LinkedMusic types, wdt:P31 exception for mb:Artist |
| `"string_matching_rules"` | Line 33: default is QID matching, exception for explicit text queries (CONTAINS/REGEX) |
| `"musicbrainz_specific"` | Line 30: mb:Work preferred over mb:Recording for Wikidata reconciliation |

Also export: `VALID_DB_NAMES = list(ONTOLOGY_CHUNKS.keys())`

**Existing file unchanged:** `llm-service/app/llm/schema_context.py` stays as-is for the fallback chain.

---

## Step 9: Enrich Example Metadata in Store

**File:** `llm-service/app/rag/store.py`

Add `enrich_example(example: dict) -> dict` that analyzes the SPARQL in each example to extract:
- `databases: list[str]` — matched by graph IRI patterns (e.g., `graphs/diamm/` → `"diamm"`)
- `challenge_level: int` — heuristic (count of GRAPH + SERVICE blocks: 1=simple, 2+=complex)
- `patterns: list[str]` — detected patterns (`"single_graph"`, `"multi_graph"`, `"federated"`, `"aggregation"`, `"string_match"`, `"cross_database"`)
- `has_federation: bool` — SPARQL contains `SERVICE`
- `has_aggregation: bool` — SPARQL contains `COUNT`/`AVG`/`SUM`/`GROUP BY`

Update `seed_store()` to include enriched metadata in Documents:
```python
docs = [
    Document(
        page_content=ex["nl"],
        metadata={"sparql": ex["sparql"], **enrich_example(ex)}
    )
    for ex in RAG_CORPUS
]
```

**Verify:** Existing `test_retrieve.py` tests pass (they mock the store).

---

## Step 10: Implement 6 Graph Nodes

**New files:** `llm-service/app/graph/nodes/{__init__,intake,retrieve,generate,validate,execute,answer}.py`

### 10a. `intake.py`

LLM-powered intent classification using structured output:

```python
class IntakeClassification(BaseModel):
    intent: Literal["lookup", "aggregation", "comparison", "path", "cross_graph"]
    target_graphs: list[Literal["diamm", "musicbrainz", "thesession", "theglobaljukebox", "digthat lick", "rism", "cantusdb"]]
    mentions_entities: bool
    needs_federation: bool
```

- Uses `ChatGoogleGenerativeAI` with `model.with_structured_output(IntakeClassification)`
- Provides list of available databases and their descriptions in the classification prompt
- Fallback on parse failure: `target_graphs=VALID_DB_NAMES, mentions_entities=True`

### 10b. `retrieve.py` (deterministic, no LLM call)

1. **Ontology lookup:** `"\n\n".join(ONTOLOGY_CHUNKS[db] for db in target_graphs)`
2. **Instruction selection** (rule-based):
   - Always: `named_graph_rules` + `output_format_rules`
   - If `mentions_entities`: + `qid_resolution_rules` + `string_matching_rules`
   - If `needs_federation` or `len(target_graphs) > 1`: + `federated_query_rules`
   - Always: + `entity_type_rules` (cheap, always useful)
   - If `"musicbrainz"` in `target_graphs`: + `musicbrainz_specific`
3. **Example retrieval:**
   - RAG enabled → filtered `similarity_search` with metadata filters by `target_graphs`/`has_federation`; fall back to unfiltered if < k results
   - RAG disabled + few_shot enabled → static `FEW_SHOT_EXAMPLES` via `format_examples()` (reuse from `app.llm.prompt`)
4. **QID pre-resolution:** if `mentions_entities`, extract capitalized multi-word sequences and call `wikidata_qid_lookup()` for each

Returns: `schema_context`, `few_shot_examples`, `resolved_qids`

### 10c. `generate.py`

SPARQL generation with tool-calling loop:

- Builds prompt from: assembled `schema_context` + `few_shot_examples` + `user_query`
- If `repair_count > 0`: prepends previous `sparql` + `validation_errors`/`execution_error` with targeted fix instructions
- If `resolved_qids` non-empty: includes as "Pre-resolved QIDs: Taylor Swift = Q26876, ..."
- Binds `wikidata_qid_lookup` tool via `model.bind_tools([wikidata_qid_lookup])`
- Runs tool-calling loop (max 3 tool call iterations): invoke → check tool_calls → execute → re-invoke
- Applies `clean_sparql()` (reuse from `app.llm.chain`) to final response
- Increments `repair_count` on repair iterations

### 10d. `validate.py`

Thin wrapper that runs both validation layers:
1. Calls `validate_sparql(state["sparql"], state.get("target_graphs"))` — syntax & safety errors
2. Calls `validate_intent(state["sparql"], state["intent"], state.get("mentions_entities", False), state.get("needs_federation", False))` — structural intent errors
3. Merges both error lists → sets `validation_errors` and `is_valid` in state

### 10e. `execute.py`

- Calls `execute_sparql(state["sparql"])` from Step 7
- On success: sets `results`, `result_count = len(results["results"]["bindings"])`
- On failure: sets `execution_error`

### 10f. `answer.py`

Two responsibilities: response assembly, and optional LLM semantic judge (gated by `settings.semantic_judge_enabled`).

**Response assembly:**
- `confidence = "high"` if valid + executed + `result_count > 0`
- `confidence = "medium"` if valid + executed + `result_count == 0`
- `confidence = "low"` if invalid or execution error after max repairs
- Collects `assumptions` from state (e.g., "Assumed QID Q26876 for Taylor Swift")

**Semantic judge** (only when `semantic_judge_enabled=True` and execution succeeded):
- Calls LLM with `user_query` + `sparql` + first 5 result rows
- Expects structured output: `{"satisfied": bool, "reason": str}`
- If `satisfied=True`: write confidence/assumptions → route to END
- If `satisfied=False` + `repair_count < max_repairs`: write `judge_feedback` → route to `generate`
- If `satisfied=False` + repairs exhausted: set `confidence="low"`, append judge reason to `assumptions` → route to END

**Routing:** node returns `"end"` or `"generate"` string; `after_answer` conditional edge in builder reads this.

**Key reuse from existing modules:**
- `app.llm.chain.clean_sparql` → generate node
- `app.llm.prompt.format_examples` → retrieve node
- `app.rag.retrieve.retrieve_examples` → retrieve node (fallback)

---

## Step 11: Node Unit Tests

**New file:** `llm-service/tests/test_graph/test_nodes.py`

~13 tests using `unittest.mock.patch` and `FakeListChatModel` (same patterns as existing `test_chain.py`):

| Node | Tests |
|------|-------|
| intake | single-graph classification, cross-graph classification |
| retrieve | correct ontology selection by target_graphs, federation rules included when needed, filtered RAG call |
| generate | SPARQL production from mock LLM, repair context injection when repair_count > 0, judge_feedback included in repair context |
| validate | valid query → is_valid=True; syntax error → is_valid=False; aggregation with no COUNT → is_valid=False; cross_graph with 1 graph → is_valid=False |
| execute | success path (mock 200), error path (mock 500) |
| answer (no judge) | high confidence with results, low confidence after max repairs |
| answer (judge=True) | satisfied=True → END; satisfied=False + repairs left → generate with judge_feedback; satisfied=False + exhausted → low confidence |

---

## Step 12: Build StateGraph + Wiring

**New file:** `llm-service/app/graph/builder.py`

### `build_graph() -> CompiledGraph`

```
StateGraph(GraphState)
  add_node("intake", intake_node)
  add_node("retrieve", retrieve_node)
  add_node("generate", generate_node)
  add_node("validate", validate_node)
  add_node("execute", execute_node)
  add_node("answer", answer_node)

  add_edge(START, "intake")
  add_edge("intake", "retrieve")
  add_edge("retrieve", "generate")
  add_edge("generate", "validate")

  add_conditional_edges("validate", after_validate, ["execute", "generate", "answer"])
  add_conditional_edges("execute", after_execute, ["answer", "generate"])
  add_conditional_edges("answer", after_answer, ["generate", END])
```

**Conditional routing:**
- `after_validate`: valid → execute; invalid + repairs left → generate; else → answer
- `after_execute`: success → answer; error + repairs left → generate; else → answer
- `after_answer`: reads routing signal from answer node — `"generate"` (judge unsatisfied + repairs left) or END (all other cases)

### `run_graph(user_query: str) -> dict`

Entry point that invokes the compiled graph, measures wall-clock time, and returns:
```python
{
    "sparql": ..., "usage": {}, "durationMs": ...,
    "graphs": ..., "confidence": ..., "assumptions": ...,
    "resultCount": ..., "executionError": ..., "results": ...
}
```

---

## Step 13: Integration Tests

**New file:** `llm-service/tests/test_graph/test_integration.py`

6 tests with mocked LLM (`FakeListChatModel`) and mocked `httpx`:

1. **Happy path** — Mock intake structured output + valid SPARQL from generate + Virtuoso 200 → `confidence="high"`, results populated
2. **Repair loop** — Invalid SPARQL first attempt (fails rdflib), valid on second → `repair_count=1`, final `confidence="high"`
3. **Max repairs exceeded** — Always invalid SPARQL → exits after `max_repairs` with `confidence="low"`
4. **Execution error triggers repair** — Valid SPARQL but Virtuoso returns error → re-enters generate with error context
5. **Structural intent check triggers repair** — `intent="aggregation"` + valid SPARQL with no COUNT → validate catches it, repair produces correct SPARQL
6. **Semantic judge triggers repair** (`semantic_judge_enabled=True`) — Judge returns `satisfied=False` on first execution, generate produces improved SPARQL, judge returns `satisfied=True` → `repair_count=1`, `confidence="high"`

---

## Step 14: FastAPI Integration with Feature Flag

**File:** `llm-service/app/main.py`

### 1. Extend TranslateResponse (backward-compatible)

```python
class TranslateResponse(BaseModel):
    sparql: str
    usage: dict
    durationMs: int
    graphs: list[str] | None = None
    confidence: str | None = None
    assumptions: list[str] | None = None
    resultCount: int | None = None
    executionError: str | None = None
    results: dict | None = None
```

### 2. LangSmith setup in lifespan

```python
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
```

### 3. Feature-flag branch in `/translate`

```python
if settings.graph_enabled:
    from app.graph.builder import run_graph  # lazy import
    result = await run_graph(req.query)
else:
    result = await translate_to_sparql(req.query)
```

**Verify:** `GRAPH_ENABLED=false uv run pytest` — all existing + new tests pass.

---

## Step 15: Docker Compose + CLAUDE.md

**Files to modify:**
- `docker-compose.dev.yml` — add env vars to `llm` service:
  ```yaml
  - GRAPH_ENABLED=${GRAPH_ENABLED:-false}
  - SEMANTIC_JUDGE_ENABLED=${SEMANTIC_JUDGE_ENABLED:-false}
  - VIRTUOSO_ENDPOINT=http://virtuoso:8890/sparql
  - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
  - LANGSMITH_PROJECT=${LANGSMITH_PROJECT:-sesemmi-agent}
  - LANGSMITH_TRACING=${LANGSMITH_TRACING:-false}
  ```
- `docker-compose.prod.yml` — same env vars
- `CLAUDE.md` — update Architecture section with LangGraph agent description, new `app/graph/` package, new env vars

---

## Execution Order & Parallelism

```
Step 1 (deps) → Step 2 (config) ─────────────────────┐
                                                       │
Steps 3,4,6,7,8 can run IN PARALLEL (independent) ───→│
Step 5 depends on Step 4                               │
Step 9 depends on Step 8                               │
                                                       ↓
Step 10 (all nodes) → Step 11 (node tests)
  → Step 12 (builder) → Step 13 (integration tests)
    → Step 14 (API integration) → Step 15 (docker/docs)
```

---

## New File Summary

| File | Purpose |
|------|---------|
| `app/graph/__init__.py` | Package |
| `app/graph/state.py` | `GraphState` TypedDict |
| `app/graph/builder.py` | `build_graph()` + `run_graph()` entry point |
| `app/graph/validation.py` | `validate_sparql()` (syntax/safety) + `validate_intent()` (structural intent checks) |
| `app/graph/nodes/__init__.py` | Package |
| `app/graph/nodes/intake.py` | Intent classification (structured LLM output) |
| `app/graph/nodes/retrieve.py` | Deterministic schema routing + filtered RAG + QID pre-resolution |
| `app/graph/nodes/generate.py` | SPARQL generation with tool-calling loop |
| `app/graph/nodes/validate.py` | Validation node (wraps validation.py) |
| `app/graph/nodes/execute.py` | Virtuoso execution node |
| `app/graph/nodes/answer.py` | Response assembly + optional LLM semantic judge (gated by `semantic_judge_enabled`) |
| `app/graph/tools/__init__.py` | Package |
| `app/graph/tools/wikidata.py` | Wikidata QID lookup (`@tool`) |
| `app/graph/tools/sparql_execute.py` | Async Virtuoso HTTP client |
| `app/rag/schema_corpus.py` | `ONTOLOGY_CHUNKS` + `INSTRUCTION_CHUNKS` dicts |
| `tests/test_graph/__init__.py` | Package |
| `tests/test_graph/test_validate.py` | Validation unit tests |
| `tests/test_graph/test_nodes.py` | Per-node unit tests |
| `tests/test_graph/test_integration.py` | End-to-end graph tests |

## Modified File Summary

| File | Changes |
|------|---------|
| `app/config.py` | +7 settings: virtuoso_endpoint, max_repair_iterations, graph_enabled, semantic_judge_enabled, langsmith_* |
| `app/main.py` | Feature-flag branch, extended response model, LangSmith setup |
| `app/rag/store.py` | `enrich_example()` + enriched metadata in `seed_store()` |
| `pyproject.toml` | +langgraph, +rdflib, +langsmith, move httpx to runtime |

## Verification Checklist

1. `uv run pytest tests/test_graph/test_validate.py -v` — all 13 validation tests pass (8 syntax/safety + 5 structural intent)
2. `uv run pytest tests/test_graph/test_nodes.py -v` — node tests pass including judge satisfied/unsatisfied paths
3. `uv run pytest tests/test_graph/test_integration.py -v` — all 6 integration tests pass
4. `uv run pytest` — ALL tests pass (existing 14 + new)
5. `GRAPH_ENABLED=false` — `/translate` uses old chain path (backward compat)
6. `GRAPH_ENABLED=true make dev` — manual E2E test with a real query
7. `SEMANTIC_JUDGE_ENABLED=true make dev` — confirm judge runs and judge_feedback appears in logs on a deliberately ambiguous query
