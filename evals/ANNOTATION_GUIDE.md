# SESEMMI Evaluation Dataset — Annotation Guide

This guide is for data annotators creating natural-language / SPARQL pairs for the SESEMMI evaluation framework. Please read it fully before writing any entries.

---

## 1. What You Are Building

Each entry is a **(question, gold SPARQL)** pair. A user asks a natural-language question about music metadata; the gold SPARQL is the correct query that answers it against the SESEMMI LinkedMusic triplestore (Virtuoso).

This dataset serves two purposes:
1. **Benchmark** for evaluating prompt engineering and RAG-based NL→SPARQL translation
2. **Publication-ready dataset** for an academic paper on NL→SPARQL over linked music data

### Dataset Partitions

| Partition | Target Size | Purpose | Rules |
|-----------|-------------|---------|-------|
| **TRAIN** | 80–100 | Few-shot examples + RAG retrieval corpus | Existing 24 entries + new gap-fillers. The RAG index is built from this set only. |
| **DEV** | 40–50 | Prompt tuning & ablation experiments | Used to compare conditions (zero-shot, few-shot, RAG, CoT). Never in prompts or RAG index. |
| **TEST** | 50–60 | Final held-out evaluation | Touched once for final paper numbers. Never seen during development. |
| **Total** | **170–210** | | |

### Why These Sizes?

These targets are calibrated against published KGQA benchmarks:

| Benchmark | Domain | Train | Dev | Test | Total |
|-----------|--------|-------|-----|------|-------|
| QALD-10 | Wikidata (general) | 412 | — | 394 | 806 |
| Scholarly QALD | DBLP/ORKG | 1,795 | 257 | 513 | 2,565 |
| LC-QuAD 1.0 | DBpedia | 4,000 | — | 1,000 | 5,000 |
| **SESEMMI (ours)** | **Music linked data** | **80–100** | **40–50** | **50–60** | **170–210** |

SESEMMI is a **domain-specific** benchmark (7 music databases, fixed schema). Our size is comparable to QALD-style benchmarks and appropriate for a domain-specific contribution where the novelty is the system architecture and RAG approach, not dataset scale.

**Statistical justification:**
- **TRAIN (80–100):** With 7 databases × 6 categories = 42 cells in the coverage matrix, ~2 examples per cell ensures meaningful RAG retrieval diversity
- **DEV (40–50):** Bootstrap confidence intervals (B=1000) become tight at n≥40; McNemar's test reaches ~15 percentage-point minimum detectable effect
- **TEST (50–60):** Sufficient for credible held-out results with narrow CIs in the paper

### Partition Rules

- **TRAIN ∩ DEV = ∅, TRAIN ∩ TEST = ∅, DEV ∩ TEST = ∅** — strictly disjoint
- DEV and TEST entries must never appear in the RAG retrieval index
- Do not copy or closely paraphrase entries across partitions
- TRAIN examples may appear in LLM prompts; DEV/TEST never do

---

## 2. Entry Format (JSON)

Each entry follows this schema (see `evals/data/schema.ts` for the TypeScript definition):

```jsonc
{
  "id": "dev-001",           // Partition prefix + 3-digit number
  "dataset": "dev",          // "train" | "dev" | "test"
  "category": "single_graph_lookup",
  "difficulty": "easy",
  "nl": "Find all sessions in Greece in The Session",
  "gold_sparql": "PREFIX ...\nSELECT ...",
  "gold_result_json": null,  // or array of result objects
  "databases": ["thesession"],
  "requires_federation": false,
  "requires_qid": true,
  "notes": "Q41 = Greece"    // optional
}
```

### Field-by-Field Instructions

#### `id`
- Format: `{partition}-{NNN}` — e.g. `dev-001`, `test-015`, `train-025`
- Must be unique across the entire dataset

#### `dataset`
- One of: `"train"`, `"dev"`, `"test"`
- Must match the file the entry lives in

#### `category`
One of six categories, mapped from the LinkedMusic challenges:

| Category | Description | Challenge Origin |
|----------|-------------|-----------------|
| `single_graph_lookup` | Query one database, return entities | Challenge 1 |
| `aggregation` | COUNT, GROUP BY, DISTINCT, ORDER BY, HAVING | Challenge 2 |
| `federated` | Uses SERVICE block to query Wikidata | Challenge 3 |
| `cross_database` | Joins data across 2+ LinkedMusic graphs | Challenge 4 |
| `string_matching` | CONTAINS, REGEX, LCASE filters | New |
| `negation_optional` | OPTIONAL, FILTER NOT EXISTS, MINUS | New |

When a query fits multiple categories, pick the **most distinctive** one. For example, a federated query with aggregation is `federated` (since that's the harder aspect).

#### `difficulty`
- **easy**: Single graph, 1-2 triple patterns, no subqueries
- **medium**: Aggregation, OPTIONAL, string filters, or 3+ triple patterns
- **hard**: Federation, cross-database joins, nested subqueries, HAVING, or complex FILTER logic

#### `nl`
The natural language question. Guidelines:
- Write as a real user would — not as a SPARQL expert
- Include the database name when it's not obvious (e.g., "in DIAMM", "in MusicBrainz")
- Use real entity names (composers, places, instruments), not Q-IDs
- Vary phrasing: "Find all...", "How many...", "Which...", "List the...", "What is the..."
- Do NOT include SPARQL syntax, property names, or graph IRIs in the question

**Good:** "Find all recordings by Miles Davis in MusicBrainz"
**Bad:** "SELECT recordings WHERE performer is wd:Q93341"

#### `gold_sparql`
The correct SPARQL query. This is the most critical field. Requirements:

1. **Must execute without errors on Virtuoso.** Test every query before submitting.
2. **Must include all necessary PREFIX declarations** at the top.
3. **Must use GRAPH clauses** — the triplestore uses named graphs, not a default graph.
4. **Must use `SELECT { GRAPH { } }` pattern**, NOT `SELECT ... FROM <graph>`.
5. **Federated queries must use subquery-before-SERVICE pattern** to avoid Virtuoso SP031 errors:
   ```sparql
   SELECT ... WHERE {
     { SELECT ... WHERE { GRAPH ... { ... } } }   # subquery first
     SERVICE <https://query.wikidata.org/sparql> { ... }  # then SERVICE
   }
   ```
6. **Never nest SELECT inside a SERVICE block.**
7. **Use `rdf:type` (or `a`) for local entity types**, not `wdt:P31`.
8. **String escaping:** Use `\n` for newlines in the JSON string value.

#### `gold_result_json`
- For small, stable result sets (< 50 rows): store the full sorted result array
- For large or volatile results: set to `null` — the eval runner will execute the gold query live
- Each result is an object whose keys are the SELECT variable names (without `?`)

Example:
```json
[
  {"capital": "http://www.wikidata.org/entity/Q1761", "capitalLabel": "Dublin"},
  {"capital": "http://www.wikidata.org/entity/Q84", "capitalLabel": "London"}
]
```

#### `databases`
Array of database identifiers the query touches. Valid values:
- `"cantusdb"`, `"diamm"`, `"dig-that-lick"`, `"thesession"`, `"theglobaljukebox"`, `"musicbrainz"`, `"rism"`

If the query also calls Wikidata via SERVICE, do NOT include Wikidata here — that's captured by `requires_federation`.

#### `requires_federation`
- `true` if the query contains a `SERVICE <https://query.wikidata.org/sparql>` block
- `false` otherwise

#### `requires_qid`
- `true` if the query references a specific Wikidata entity (e.g., `wd:Q200580`)
- `false` if all filtering is on literal values or structural patterns only

#### `notes` (optional)
Free-text notes for annotators and debuggers. Use for:
- Documenting which Q-ID maps to which entity (e.g., "Q200580 = Guillaume de Machaut")
- Flagging known issues or edge cases
- Explaining why a particular query pattern was chosen

---

## 3. The 7 Databases — Quick Reference

| Database | Graph IRI | Type Prefix | Key Entity Types |
|----------|-----------|-------------|-----------------|
| Cantus DB | `cdb:` = `<https://linkedmusic.ca/graphs/cantusdb/>` | `cdb:` | Chant, Source |
| DIAMM | `diamm:` = `<https://linkedmusic.ca/graphs/diamm/>` | `diamm:` | Archive, City, Composition, Country, Organization, Person, Region, Set, Source |
| Dig That Lick | `dtl:` = `<https://linkedmusic.ca/graphs/dig-that-lick/>` | `dtl:` | Solo, Track |
| The Session | `ts:` = `<https://linkedmusic.ca/graphs/thesession/>` | `ts:` | Events, Member, Recording, Session, Tune, TuneSetting |
| Global Jukebox | `gj:` = `<https://linkedmusic.ca/graphs/theglobaljukebox/>` | `gj:` | Culture, Ensemble, Instrument, Minutage, Parlametrics, Phonotactics, Song, Source |
| MusicBrainz | `mb:` = `<https://linkedmusic.ca/graphs/musicbrainz/>` | `mb:` | Area, Artist, Event, Genre, Instrument, Label, Place, Recording, Release, ReleaseGroup, Series, Work |
| RISM | `rism:` = `<https://linkedmusic.ca/graphs/rism/>` | `rism:` | Exemplar, Incipit, Institution, Person, Place, Source, Subject |

### Common Wikidata Properties Used

| Property | Meaning | Notes |
|----------|---------|-------|
| `wdt:P2888` | exact match | Links local entity → Wikidata URI |
| `wdt:P86` | composer | |
| `wdt:P175` | performer | |
| `wdt:P136` | genre | |
| `wdt:P17` | country | |
| `wdt:P826` | tonality / mode | |
| `wdt:P276` | location | |
| `wdt:P870` | instrumentation | |
| `wdt:P495` | country of origin | |
| `wdt:P2596` | culture | Global Jukebox specific |
| `wdt:P527` | has part | |
| `wdt:P361` | part of | |
| `wdt:P3440` | time signature | |
| `wdt:P569` | date of birth | |
| `wdt:P570` | date of death | |
| `wdt:P571` | inception | |
| `wdt:P576` | dissolved date | |
| `wdt:P21` | sex or gender | |
| `wdt:P264` | record label | |
| `wdt:P1922` | incipit | RISM specific |
| `wdt:P8546` | recording location | |

For the full ontology, see `src/lib/llm/schema-context.ts`.

---

## 4. Coverage Targets

### Coverage Matrix

The dataset should cover the full cross-product of **7 databases × 6 categories**. Not every cell needs entries (some combinations are rare, e.g., `negation_optional` + `dig-that-lick`), but aim for broad coverage.

### TRAIN set (80–100 entries)

Starting from the existing 24 examples, add 56–76 new entries. Priority gap-fillers:

| Category | Current | Target | Priority Gaps |
|----------|---------|--------|---------------|
| `single_graph_lookup` | 7 | 15–18 | Add variety in entity types and filters |
| `aggregation` | 7 | 15–18 | Add HAVING, multiple GROUP BY, subqueries |
| `federated` | 6 | 15–18 | More Wikidata properties (P19, P106, P1082, etc.) |
| `cross_database` | 4 | 15–18 | Cover more database pairs (21 possible pairs) |
| `string_matching` | 0 | 10–14 | CONTAINS, REGEX, LCASE — currently zero coverage |
| `negation_optional` | 0 | 10–14 | OPTIONAL, FILTER NOT EXISTS — currently zero coverage |

**Database coverage:** Every database should appear in at least 8 TRAIN entries. MusicBrainz and DIAMM (richest schemas) may have more.

**RAG note:** TRAIN entries form the retrieval corpus for the LangChain RAG agent. Good coverage here directly improves RAG retrieval quality.

### DEV set (40–50 entries)

| Category | Target Count | Database Coverage |
|----------|-------------|-------------------|
| `single_graph_lookup` | 8–10 | All 7 databases represented |
| `aggregation` | 8–10 | Mix of COUNT, GROUP BY, HAVING, DISTINCT |
| `federated` | 8–10 | Different SERVICE patterns and Wikidata properties |
| `cross_database` | 8–10 | At least 6 different database pairs |
| `string_matching` | 4–5 | CONTAINS, REGEX, case-insensitive |
| `negation_optional` | 4–5 | OPTIONAL, FILTER NOT EXISTS, MINUS |

### TEST set (50–60 entries)

| Category | Target Count | Database Coverage |
|----------|-------------|-------------------|
| `single_graph_lookup` | 10–12 | All 7 databases represented |
| `aggregation` | 10–12 | |
| `federated` | 10–12 | |
| `cross_database` | 10–12 | |
| `string_matching` | 5–6 | |
| `negation_optional` | 5–6 | |

### Difficulty Distribution (per set)

| Difficulty | Proportion | Notes |
|------------|-----------|-------|
| **easy** | ~30% | Single graph, 1-2 triple patterns |
| **medium** | ~40% | Aggregation, OPTIONAL, string filters |
| **hard** | ~30% | Federation, cross-database, nested subqueries |

### Database Pair Coverage (cross_database entries)

There are 21 possible database pairs. Across TRAIN + DEV + TEST combined, aim to cover at least 12 unique pairs. Priority pairs (most likely in real usage):

| Pair | Why |
|------|-----|
| DIAMM ↔ RISM | Shared composers via wdt:P2888 |
| MusicBrainz ↔ Dig That Lick | Shared performers/tracks |
| MusicBrainz ↔ The Session | Shared events/tunes |
| Global Jukebox ↔ The Session | Shared countries |
| Global Jukebox ↔ MusicBrainz | Shared instruments via wdt:P2888 |
| DIAMM ↔ Cantus DB | Shared manuscripts/sources |
| RISM ↔ Cantus DB | Shared liturgical content |

---

## 5. Finding Wikidata Q-IDs

To find the correct Q-ID for an entity:

1. **Search Wikidata**: Go to `https://www.wikidata.org/` and search for the entity
2. **Verify against the triplestore**: Run a query to confirm the Q-ID exists in the data:
   ```sparql
   PREFIX wd:  <http://www.wikidata.org/entity/>
   PREFIX wdt: <http://www.wikidata.org/prop/direct/>
   SELECT ?entity WHERE {
     GRAPH <https://linkedmusic.ca/graphs/diamm/> {
       ?entity wdt:P2888 wd:Q200580 .
     }
   }
   ```
3. **Document the mapping** in the `notes` field: `"Q200580 = Guillaume de Machaut"`

**Never guess Q-IDs.** If you can't verify a Q-ID exists in the triplestore, choose a different entity.

---

## 6. Query Verification Checklist

Before submitting each entry, verify:

- [ ] The `gold_sparql` executes without errors on Virtuoso
- [ ] The query returns non-empty results (unless testing a valid empty-result case)
- [ ] All PREFIX declarations are present
- [ ] GRAPH clauses wrap all triple patterns for LinkedMusic data
- [ ] Federated queries use subquery-before-SERVICE pattern
- [ ] The `nl` question is natural and does not reveal SPARQL internals
- [ ] The `category`, `difficulty`, `databases`, `requires_federation`, and `requires_qid` fields are accurate
- [ ] The `id` is unique and follows the `{partition}-{NNN}` format
- [ ] The entry does not duplicate or closely paraphrase any entry in another partition
- [ ] Q-IDs are documented in the `notes` field

---

## 7. Common Mistakes to Avoid

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Using `FROM <graph>` instead of `GRAPH {}` | Virtuoso requires GRAPH clause syntax | Always use `GRAPH <iri> { ... }` |
| SERVICE inside GRAPH or OPTIONAL | Virtuoso error | SERVICE must be at the top level |
| Nested SELECT inside SERVICE | Wikidata endpoint rejects this | Flatten the query |
| Missing subquery before SERVICE | Causes Virtuoso SP031 error | Wrap local graph patterns in a subquery |
| Using `wdt:P31` for local type checks | LinkedMusic uses `rdf:type` (`a`) for classes | Use `?x a diamm:Composition` |
| Hallucinated Q-IDs | Entity doesn't exist in the triplestore | Always verify Q-IDs with a test query |
| Copying TRAIN examples to DEV/TEST | Data leakage invalidates results | Write genuinely new questions |
| NL question reveals SPARQL syntax | Unrealistic user input | Rephrase naturally |
| Same question in DEV and TEST | Leakage during tuning | Cross-check across all partitions |

---

## 8. Inspiration Sources

Good sources for new questions (the NL part):

1. **LinkedMusic wiki sample queries** — 14 unimplemented NL queries listed at the bottom of the [Sample Queries page](https://github.com/DDMAL/linkedmusic-datalake/wiki/Sample-LinkedMusic-Queries)
2. **Musicology research questions** — think about what a music researcher would ask
3. **Cross-database discovery** — "which entities appear in both X and Y?"
4. **Temporal queries** — birth/death dates, inception years, publication dates
5. **Geographic queries** — countries, cities, continents, regions
6. **Statistical questions** — "how many", "what percentage", "most common"
7. **Negative/absence queries** — "which X don't have Y?", "are there any X without Z?"
8. **Comparison queries** — "which database has more X?", "compare X across Y and Z"

### Example Questions by Category

**single_graph_lookup:**
- "Find all jazz recordings in MusicBrainz"
- "What instruments appear in Global Jukebox?"

**aggregation:**
- "Which DIAMM archive has the most sources?"
- "How many solos per instrument in Dig That Lick?"

**federated:**
- "Find MusicBrainz artists born in Japan"
- "What is the population of countries with RISM institutions?"

**cross_database:**
- "Find compositions that appear in both DIAMM and RISM"
- "Which Dig That Lick performers also have MusicBrainz recordings?"

**string_matching:**
- "Find all tunes in The Session with 'waltz' in the name"
- "Search for RISM sources mentioning 'requiem'"

**negation_optional:**
- "Find MusicBrainz artists without a known birth date"
- "Which DIAMM sources have no associated compositions?"

---

## 9. Annotation Workflow

### Recommended Order

1. **Start with TRAIN gap-fillers** (priority: `string_matching` and `negation_optional` which have zero coverage)
2. **Then DEV entries** — these will be used first for prompt tuning experiments
3. **Finally TEST entries** — write these last, when you're most familiar with the schema

### Batching

- Work in batches of 10–15 entries
- After each batch: validate all queries against Virtuoso, cross-check for duplicates
- Submit a PR per batch for review

### Quality > Quantity

A verified entry with a correct gold query is worth more than five unverified entries. Every gold SPARQL must execute correctly — broken queries waste evaluation cycles.

---

## 10. Submitting Your Work

1. Save entries in the appropriate JSON file: `evals/data/train.json`, `evals/data/dev.json`, or `evals/data/test.json`
2. Ensure the JSON is valid (use a JSON linter)
3. Run the verification checklist (Section 6) for every entry
4. Cross-check: no entry in your batch duplicates or paraphrases an entry in another partition
5. Submit a PR with your additions
