# Cross-database sample-query design guide

This guide is for designing new entries in [`examples.py`](examples.py)'s `FEW_SHOT_EXAMPLES` list. The site shows these as sample SPARQL queries, so they must look polished and make LinkedMusic look comprehensive. The current focus is queries that **feature CKG (NFDI4Culture) feeds heavily** — that means at least one or two of `ckg-apsearch`, `ckg-detmold`, `ckg-musiconn` should appear in your query — but **not necessarily all three**, and the query should also draw from non-CKG graphs (MusicBrainz, RISM, DIAMM, Global Jukebox, The Session, etc.). Going forward, 1–2 CKG feeds per query is sufficient.

## What "sample query for the site" means in practice

- The result table needs to look populated. **Don't ship a query whose result has a column that's mostly zeros** — it makes us look like we have data gaps even when the zeros are historically real (e.g., recordings before 1900 don't exist because phonography didn't exist).
- The NLQ must sound like something a working musicologist would ask without knowing our schema. Don't say "ckg-detmold" or "musiconn"; say "court-theatre repertoire" or "public concert events."
- Wikidata `SERVICE` calls are rate-limited and have broken queries in the past. Minimize or avoid them.
- Validate every query end-to-end on prod before adding it. A query that looks clean but returns mostly-empty cells should be redesigned, not shipped.

## Prod endpoint

- `https://virtuoso.simssa.ca/sparql`. Single endpoint, all graphs loaded — no federation needed.
- Staging is gone. Validate locally with `curl -G ... --data-urlencode "query=..." -H "Accept: application/sparql-results+json"`.

## What's in each feed (verified 2026-06-22)

### CKG feeds — pick 1–2 per query

**`<https://linkedmusic.ca/graphs/ckg-apsearch/>`** — Arabic Phonogram Search (BBAW). **Ethnographic Arabic field-recording archive, 20th/21st century.** Only `apsearch:Work` (6,271). No `Person`, no `Place`. Predicates: `rdfs:label`, `wdt:P31`, `wdt:P123`, `wdt:P275`, `wdt:P571` (recording date, range 1900–2018, sparse before 2010), `wdt:P953`, `cto:CTO_0001006`, `cto:CTO_0001026`. Labels are Arabic folk content ("sung nana", "Children's rhymes", "Taqsīm raṣd"). **Do not try to bridge Western composers into apsearch via label-match — there is no Western art-music content.** Best featured in queries about ethnographic/non-Western recordings or 20th–21st century recording activity, not Western 19th-c. music.

**`<https://linkedmusic.ca/graphs/ckg-detmold/>`** — Detmolder Hoftheater. **19th-c. German court theatre repertoire.** Classes: `Work` (1,694), `Person` (570), `Place` (38). `Work.wdt:P571` = composition date, range 1605–1904, peak 1820s–40s (45–50 works/decade). `Work.cto:CTO_0001009` → related person (mostly librettists/playwrights, NOT composers). `Person.wdt:P2888` → Wikidata QID. Top related-persons by work count: Eugène Scribe (Q319261, 146 works, French librettist), August von Kotzebue (Q57242, 105, German playwright), Karl Eduard von Holtei (Q66388, 92), Louis Schneider (Q214659, 74), Louis Angely (Q76070, 60). Of the canonical 19th-c. opera composers, only Rossini (Q9726, 8 works) and Verdi (Q7317, 2 works) appear; Lortzing (Q150804), Flotow (Q57271), Auber (Q170069), Donizetti (Q34522), and Haydn (Q7349) are not present.

**`<https://linkedmusic.ca/graphs/ckg-musiconn/>`** — musiconn.performance. **Rich European concert/performance history.** Classes: `Event` (65k), `Work` (41k), `Person` (20k), `Place` (6k), `Organization` (3.5k), `Collection` (1.3k). `Event.wdt:P585` = performance date (well populated). `Event.cto:CTO_0001011` = venue. `Event.cto:CTO_0001009` = related person (sparse — only 4,343 events; **mostly conductors/soloists, not composers**). `Event.cto:CTO_0001019` = related work (277,812 triples — well populated). `Work.cto:CTO_0001009` = related person → this is the **composer-attribution path**: `Event → cto:CTO_0001019 → Work → cto:CTO_0001009 → Person → wdt:P2888`. `Work` has **no `wdt:P571`** — work composition dates are not in musiconn. `Person.wdt:P2888` → Wikidata QID. Via the composer-attribution path: Bach has 10,738 events; Beethoven 7,676; Mozart 6,283; Brahms 5,427.

### Other databases — date predicates inventory

Verified date predicates for use in temporal queries:

| Graph | Class | Date predicate | Count | Useful range |
| --- | --- | --- | --- | --- |
| musicbrainz | Recording | `wdt:P577` (publication date) | 835,774 | post-1950 mostly (1910s: 5, 1920s: 29, 1950s: 3.6k, 1980s: 34k) |
| musicbrainz | Event | `wdt:P580` (start time) | 100,939 | 1790s onward, ~900 in 1790–1920 window |
| musicbrainz | Event | `wdt:P585` (point in time) | 35,243 | overlaps with P580 |
| musicbrainz | Work | — | — | **No date predicates work on MB Work.** |
| thesession | Events | `wdt:P580` | 7,947 | post-2000 (contemporary Irish trad community) |
| thesession | Recording | — | — | No date predicates work. |
| theglobaljukebox | Song | `wdt:P585` | 5,581 | mostly 1930s–1980s (peak 1950s with 2,076) |
| dig-that-lick | Solo / Track | — | — | No date predicates work. |
| rism | Source | — | — | No `wdt:P571/P577/P580/P585` work. (Manuscripts have textual date statements, not Wikidata-typed dates.) `wdt:P86` = composer (55k links to 9 canonical composers); `wdt:P50` is present but **only 11 hits total** for canonical composers — use P86. |
| diamm | Composition | — | — | No standard date predicates work. |
| utsi | Song / Anthology | — | — | No date predicates work. |
| cantusdb | Chant / Source | — | — | No date predicates work. |

**Bottom line on temporal queries**: only detmold:Work + P571, musiconn:Event + P585, mb:Event + P580/P585, mb:Recording + P577, gj:Song + P585, thesession:Events + P580, and apsearch:Work + P571 are usable. Other databases need non-temporal questions.

### Composer-attribution paths (verified)

For composer-centric queries, these are the working paths from each item to a Wikidata composer QID (verified against 9 canonical composers: Bach Q1339, Mozart Q254, Haydn Q7349, Beethoven Q255, Schubert Q7312, Mendelssohn Q46096, Schumann Q7351, Brahms Q7294, Wagner Q1511. Verdi Q7317 was a notable confusion point — the original guide listed Verdi as Q7349, which is actually Haydn). All other graphs (simssa, diamm, thesession, theglobaljukebox, dig-that-lick, cantusdb, apsearch) return **0 hits** for these QIDs and should not be queried for composer-centric work.

| Graph | Item class | Path to composer QID | Per-composer scale |
| --- | --- | --- | --- |
| ckg-musiconn | Event | `?ev cto:CTO_0001019 ?work . ?work cto:CTO_0001009 ?p . ?p wdt:P2888 ?qid` | 2k–11k |
| ckg-detmold | Work | `?work cto:CTO_0001009 ?p . ?p wdt:P2888 ?qid` | 0–6 (sparse; mostly librettists) |
| musicbrainz | Work | `?w wdt:P86 ?a . ?a wdt:P2888 ?qid` | 665–7,318 |
| musicbrainz | Recording | `?r wdt:P2550 ?w . ?w wdt:P86 ?a . ?a wdt:P2888 ?qid` | 14k–120k |
| musicbrainz | Release | `?rel wdt:P175 ?a . ?a wdt:P2888 ?qid` | thousands (artist-credited) |
| musicbrainz | ReleaseGroup | `?rg wdt:P175 ?a . ?a wdt:P2888 ?qid` | thousands (artist-credited) |
| rism | Source | `?s wdt:P86 ?p . ?p wdt:P2888 ?qid` | 390–17,179 |
| utsi | Song | `?s wdt:P86 ?qid` (direct, no intermediate person node) | 0–hundreds |

**Watch out:**

- `wdt:P175` on MB Recording/Release is **performer/artist-credit**, not composer. For "recordings of works by composer X", use the 2-hop path through `wdt:P2550 → Work → wdt:P86`. `wdt:P175` on Recording for canonical composers returns near-zero (e.g., Mozart = 26 because he was dead before recording technology existed).
- UTSI is the only graph that links works directly to the Wikidata QID without an intermediate person node.
- MB stores its own `rdfs:label` for each reconciled artist — useful for displaying names in result tables without a Wikidata SERVICE call. Sanity-check unfamiliar QIDs against this label before writing them into a query — the earlier version of this guide listed Verdi as Q7349, but Q7349 is Haydn (Verdi is Q7317). When in doubt, look up the label in MB.

## Cross-feed joining — what works

- **`wdt:P2888` Person → Wikidata QID**: detmold ↔ musiconn ↔ mb ↔ diamm ↔ rism. The strongest cross-archive bridge. Apsearch has no Person, so it's not part of this network. UTSI uses the QID directly on items (no intermediate Person node) but still cross-joins via the same QID.
- **`cto:CTO_0001009` (related person)** inside CKG (detmold and musiconn) bridges Work to Person, which then bridges to Wikidata via `wdt:P2888`. On musiconn, this predicate fires on `Work` but only sparsely on `Event` — composer-attribution for Events runs via `Event → cto:CTO_0001019 → Work → cto:CTO_0001009 → Person`, not directly off the Event.
- **Parallel temporal aggregation**: `UNION` three or more per-graph patterns, each binding a counter (1/0), `SUM` and `GROUP BY` on year/decade.
- **All-archive aggregate**: `UNION` per-path subqueries that each return `(?composer, ?n)`, then `SUM(?n)` in the outer aggregation to collapse to a single total column. See Pattern 4.

## What doesn't work — don't waste time

- **`wdt:P123` (publisher) on CKG works**: returns a single feed-level institutional ID per graph (apsearch → E2431, musiconn → E1841, detmold → E2427/E2873). Joining feeds on `?work wdt:P123 ?pub` yields 0 shared publishers — don't use this as a cross-feed bridge.
- **`cto:CTO_0001006`** is a feed-level type marker, same story.
- **Label string-matching apsearch against Western composers**: apsearch is Arabic folk content, returns nothing.
- **`cto:CTO_0001011` (place)** for 3-way CKG joins: apsearch has no place links.
- **MB Recording in pre-1920 windows**: ~5 dated recordings before 1920, ~29 in the 1920s. Phonography didn't exist yet — no database can fill this in. Don't design temporal queries that need rich pre-1920 recording data.
- **`wdt:P50` on RISM** for composers: P50 is "author" (textual), used for librettists/text-authors, not composers. Returns 11 hits total across the 9 canonical composers vs. 55,706 via `wdt:P86`. Always use P86 on RISM for composer attribution.
- **`wdt:P175` on MB Recording** as a composer link: P175 is performer. Mozart (Q254) returns only 26 recordings via P175 (vs. 76,009 via the P2550→P86 path). For dead composers, P175 hits are catalog-metadata noise.
- **SIMSSA, DIAMM, theglobaljukebox, thesession, dig-that-lick, cantusdb** for canonical Western art-music composers: each returns 0 hits via any standard composer-linkage predicate. SIMSSA has only 92 composer-work triples total; DIAMM is medieval-only; the others cover non-classical or chant traditions. Don't include them in composer-centric queries.
- **Wikidata `SERVICE`**: rate-limited, has been a known pain point ([memory: `project_sesemmi_goal`](../../../../../../../../.claude/projects/-Users-Liam-Documents-Main-School-MasterDegree-DDMAL-GitHub-linkedmusic-datalake/memory/project_sesemmi_goal.md)). Avoid unless the question genuinely needs it.

## Honest situation across the three CKG feeds

- **detmold** and **musiconn** are tightly joinable via `wdt:P2888` on `Person` and share a Western European art-music focus. Cross-DB joins with MB/RISM/DIAMM via the same QID work well.
- **apsearch** is the odd one out: no Person, no Place, no composer attribution, content is Arabic ethnographic field recordings. It will not participate naturally in composer-centric or Western-music-historiography queries. It is best featured in *its own* dedicated queries about ethnographic recording, non-Western traditions, or 20th–21st century recording activity. Don't force it into queries where it would just contribute zeros.

## Patterns that work for sample queries

### 1. Decade-binned temporal aggregation (works well for 19th c.)

```sparql
SELECT ?decade (SUM(?a) AS ?colA) (SUM(?b) AS ?colB)
WHERE {
  { GRAPH g1: { ?x a g1:Class ; wdt:Pn ?date }
    BIND(xsd:integer(CONCAT(SUBSTR(STR(?date), 1, 3), "0")) AS ?decade)
    BIND(1 AS ?a) BIND(0 AS ?b) }
  UNION
  { GRAPH g2: { ?y a g2:Class ; wdt:Pn ?date }
    BIND(xsd:integer(CONCAT(SUBSTR(STR(?date), 1, 3), "0")) AS ?decade)
    BIND(0 AS ?a) BIND(1 AS ?b) }
  FILTER(?decade >= 1800 && ?decade < 1900)
}
GROUP BY ?decade ORDER BY ?decade
```

The currently-shipped sample uses this shape with detmold:Work + musiconn:Event + mb:Event over 1800–1900, telling the story of court-patronage decline + public-concert rise. Two columns is fine — three or more is fine if the data populates them, but don't fake breadth.

### 2. Composer-centric multi-archive aggregation, one column per archive

```sparql
SELECT ?composer ?countA ?countB ?countC ...
WHERE {
  { SELECT ?composer (COUNT(DISTINCT ?w) AS ?countA) WHERE { GRAPH g1: { ... } } GROUP BY ?composer }
  OPTIONAL { SELECT ?composer (COUNT(DISTINCT ?e) AS ?countB) WHERE { GRAPH g2: { ... } } GROUP BY ?composer }
  ...
}
ORDER BY DESC(?countA) LIMIT 15
```

Use **VALUES inside each subquery** to scope each aggregation to a fixed composer list, otherwise the planner does full-graph scans and times out (24,000+ sec estimated for cartesian joins on top-15 musiconn composers).

Tested per-composer numbers via `wdt:P2888` for Beethoven (Q255): 7,676 musiconn events, 2 detmold works, 2,820 MB works, 66,918 MB recordings (via P2550→P86), 4,573 RISM sources (via P86), 0 DIAMM compositions (medieval-only). Apsearch doesn't fit this shape (no Person).

**Caveat — sparse columns**: detmold has only 0–6 works per canonical composer (its catalog skews to librettists, not composers); DIAMM has 0 for everyone post-medieval. Don't ship those as separate columns. Either drop them or use Pattern 4 below.

### 3. Apsearch's own dedicated queries

When you want apsearch to feature prominently, ask questions about ethnographic field recordings, oral traditions, recording-era cultural archiving, or anything where Arabic folk content is the topic. Don't try to bridge to detmold/musiconn — they're separate musical worlds.

### 4. All-archive composer footprint (single total column)

When the question is "how comprehensively does the datalake cover composer X", sum across every contributing graph into one column. This collapses the per-archive sparsity problem and shows total reach. Use a UNION of per-path subqueries, each returning `(?composer, ?n)`, then `SUM(?n)` in the outer aggregation:

```sparql
SELECT ?composer ?name (SUM(?n) AS ?totalItems)
WHERE {
  { SELECT ?composer (SAMPLE(?lbl) AS ?name) WHERE { VALUES ?composer { ... } GRAPH mb: { ?a wdt:P2888 ?composer ; rdfs:label ?lbl } } GROUP BY ?composer }
  {
    { SELECT ?composer (COUNT(DISTINCT ?e) AS ?n) WHERE { VALUES ?composer { ... } GRAPH musiconn: { ... } } GROUP BY ?composer }
    UNION
    { SELECT ?composer (COUNT(DISTINCT ?w) AS ?n) WHERE { VALUES ?composer { ... } GRAPH detmold: { ... } } GROUP BY ?composer }
    UNION
    ...one branch per (graph, item-class) path from the inventory above...
  }
}
GROUP BY ?composer ?name
ORDER BY DESC(?totalItems)
```

Each branch must `VALUES`-scope ?composer internally — same reason as Pattern 2. The name lookup is a separate subquery joined on ?composer so it always populates regardless of which UNION branches fire. Tested over all 8 contributing paths (musiconn, detmold, mb:Work, mb:Recording, mb:Release, mb:ReleaseGroup, rism, utsi): Bach 161,293; Mozart 118,221; Beethoven 95,711; down to Wagner 24,081. Each composer is non-zero across multiple contributing graphs, so the total is honest, not driven by one archive.

## SPARQL/Virtuoso quirks

- **No `%` modulo operator.** For decade binning, use either:
  - `xsd:integer(FLOOR(YEAR(?d) / 10) * 10)` — works if `?d` is guaranteed clean `xsd:date`.
  - `xsd:integer(CONCAT(SUBSTR(STR(?d), 1, 3), "0"))` — string-based, robust to malformed literals. **Prefer this** if any MusicBrainz date is in the union.
- **MusicBrainz date literals are sometimes malformed** (e.g., textual fragments). `YEAR(?d)` crashes the whole query with "Incomplete RDF box as argument 0 for year()". Use `STR(?d) >= "1800" && STR(?d) < "1900"` for filtering and `SUBSTR(STR(?d), 1, 3)` for year extraction.
- **`BIND` inside `UNION` branches** works per-branch; that's how the temporal-counter pattern works.
- ISQL (CLI) requires the `SPARQL` keyword prefixed on every statement ([memory: `reference_isql_sparql_prefix`](../../../../../../../../.claude/projects/-Users-Liam-Documents-Main-School-MasterDegree-DDMAL-GitHub-linkedmusic-datalake/memory/reference_isql_sparql_prefix.md)). The HTTP endpoint does not.

## Existing CKG examples

`examples.py` already contains CKG-touching queries covering single-graph type lookups, single-graph aggregations (publisher/place/person counts), Wikidata `SERVICE` federation (rate-limit-flaky in production — see warning above), cross-graph joins via `wdt:P2888`, decade-binned temporal aggregations, all-archive composer-footprint sums, and apsearch-dedicated ethnographic queries. Read what's already there before adding new entries to avoid duplication, and skim them to confirm your new query isn't shadowing an existing pattern.

## How to validate before shipping

1. Run the SPARQL against `https://virtuoso.simssa.ca/sparql` and look at the result table.
2. If any column is mostly zeros: redesign. Either drop the column, change the window, change the question, or — for breadth queries — switch to Pattern 4 (sum the sparse columns into a single total). Don't ship a sparse separated-column result.
3. Read the NLQ back. If it sounds like a database question rather than a musicology question, rewrite it. Don't reference graph names or schema artifacts.
4. Check whether the result tells a coherent musicological story. If the answer would not change a musicologist's understanding of anything, the question is too trivial or too contrived.
5. Confirm no `SERVICE <https://query.wikidata.org/sparql>` clause is used unless absolutely necessary.
6. Confirm the query touches at least one CKG feed (currently expected: 1–2 per query).

## Output format

Each entry in `FEW_SHOT_EXAMPLES`:

```python
{
    "nl": "<natural-language question, end-user phrasing>",
    "sparql": """<PREFIX block>
<query body>""",
},
```

Existing examples use 4-space PREFIX alignment and triple-quoted strings starting with the first PREFIX directly after `"""`. Match that style.
