# SESEMMI reliability review — 16 September 2026

## Scope and evidence

This pass uses the existing five UI questions and authored few-shot pairs. It
includes offline syntax/schema checks, mocked application tests, and bounded,
read-only Virtuoso/Wikidata checks. **No paid model calls, production writes or
deployment were performed.** No improvement in model accuracy or latency has
yet been measured.

The reusable data probes check available relationships, not complete answers to the
questions. Returning rows is not a correctness test. The current questions and
their expected limitations are in [reliability_cases.json](reliability_cases.json).
Raw endpoint responses and generated audit reports are local artifacts under
`eval/audits/`, which is ignored by Git. Tests do not require that directory.
The dated observations below are a summary; later runs may produce different counts
or convenience samples.

## Changes

This section summarizes the topic-specific reliability PR series. The audit-tools
PR supplies the reusable scripts and this findings summary; the application changes below are
in companion PRs.

- Preserve database descriptions, reconciliation notes and query notes when
  slicing ontologies. Previously, only prefixes and selected class blocks reached
  the generator and judge. Expanded notes explain direct QIDs versus local nodes,
  roles, date meanings, broad instrument mappings and missing classifications.
- An empty ASK probe is evidence for the judge, not an automatic repair request.
  Generation/repair instructions preserve required entities, filters and databases.
- A failed external SERVICE is reported as unavailable. Its error is retained and
  does not trigger another model round. Automatically removing SERVICE could remove
  a required birthplace or other condition, so that fallback has been removed.
- Title matches, shared categories and shared dates no longer imply entity identity.
  A model-accepted partial answer stays at medium confidence; a rejected answer is
  low. Execution alone, or an unavailable judge, cannot award high confidence.
- Send assumptions through the streaming response and display them beside the
  generated query. Hide those notes after manual query edits, since the earlier
  assessment no longer applies. Headings are translated; generated notes currently
  retain the backend's English, like the other backend diagnostics.
- Correct RAG's Weimar database key (`weimarjazz`) and preserve relevant examples
  when filling unused retrieval slots. Fall back to the full database schema when
  the planner selects no valid classes.
- Cache only deterministic ontology parsing. Model selection, semantic judging,
  retrieval depth and repair limits remain available; no model stage was skipped
  for speed. The router also enforces the repair limit on judge feedback.
- Remove conflicting instructions that forced a URI-only answer to aggregation
  questions or required English tags on untagged source labels.
- Unit tests block socket connections and use a local dummy provider so a missing
  mock cannot spend credits or query production.

## Few-shot audit

There are **178 authored pairs**, rather than approximately 158. The historical
`samples_apr13.csv` contains 106 rows and is not the current runtime corpus.

| Finding | Change |
| --- | --- |
| Cantus Saint Stephen example lacked `PREFIX wdt:` | Added it. |
| Eleven examples relied on an implicit `xsd:` prefix | Added explicit declarations. RDFLib predefines this namespace, so an ordinary parse check alone misses the issue. |
| The authored MusicBrainz schema incorrectly excluded Work, ReleaseGroup, Series and Recording → Work | Corrected the schema against the live endpoint and restored the death-title Work branch. |
| Three MusicBrainz examples were initially excluded using that stale schema | Restored unchanged after their original queries returned live results. The earlier unsupported-class conclusion was wrong. |
| APSearch/BBAW question promised Arabic field recordings, but its query selected generic works within an unrequested date range | Replace it with an explicit audio-type query and a question about catalogued creation years. Correct the same unsupported wording in seven related questions. |

All **178 examples** are active and pass the offline syntax, explicit-prefix and documented
graph/class/predicate checks. This does **not** certify semantic correctness, live
executability, individual QIDs or answer completeness. See the reproducible
[backend regression tests](../llm-service/tests/test_examples.py). These checks run
in ordinary CI; no standalone corpus-audit CLI or generated report is needed.

### Correction from live MusicBrainz verification

The 16 September 2026 live check found **2,459,169 Work instances** and
**3,790,920 ReleaseGroup instances**, plus Series and Recording → `P2550` → Work links. Absence from an
authored schema is not evidence of absence from the database.

The four original queries affected by the incorrect schema conclusion all ran:

| Original example | Rows returned |
| --- | ---: |
| Charlie Parker works via Dig That Lick (#24) | 4 |
| Compositions/recordings with “death” in the title (#25) | 7,412 |
| Opera-composer archive comparison (#142) | 10 |
| Overall composer footprint (#146) | 9 |

The four original queries remain in [the authored corpus](../llm-service/app/graph/examples.py).
The live checks establish
live support and execution; they do not independently certify every role,
archive-coverage assumption or cross-archive counting interpretation. The separate
APSearch/BBAW correction is described below. No examples remain quarantined; the
`review_required` flag and separate authored/runtime lists have been removed.

### APSearch correction for manual verification

`review_required` was a manually assigned exclusion reason, not a model verdict or
an endpoint error. It kept the authored pair out of both static few-shot and RAG
context. The remaining flag has now been resolved by correcting the pair.

Eight bounded, read-only endpoint queries on 16 September 2026 established:

- The original BBAW query (#138) executes and returns 100 rows. All 100 carry only
  `Q17537576` (generic creative work); those results do not establish audio type,
  Arabic language, or field-recording status.
- The publisher path is correct: `P123` points to NFDI4Culture `E2431`, which has
  `P2888` → `Q219989` (BBAW). All 6,271 works have this publisher.
- The graph has 3,005 explicitly typed audio records, 2,409 with creation years.
  It also contains images, videos, texts and generic works. No structured language
  or field-recording property is present in the graph's predicate inventory.
- The APSearch converter's `coerce_date` maps source creation intervals to
  `xsd:gYear` of the start year, discarding the end year. These are catalogued
  creation years, not independently verified recording dates.

The [source feed description](https://nfdi4culture.de/resource/E6304/about.html)
describes Arabic phonograms at the collection level. That context is useful, but
does not establish every record's language or distinguish field recordings from
other content. The [publisher record](https://nfdi4culture.de/resource/E2431/about.html)
confirms BBAW.

The revised #138 question asks for **up to 100 records explicitly classified as
audio recordings, published by BBAW, with their catalogued creation years, earliest
first**. This deliberately changes the question to match verifiable data. It does
not claim to answer the original Arabic-field-recording request. The corrected
query returned 100 rows, beginning in 1970:

```sparql
PREFIX wd:       <http://www.wikidata.org/entity/>
PREFIX wdt:      <http://www.wikidata.org/prop/direct/>
PREFIX apsearch: <https://linkedmusic.ca/graphs/ckg-apsearch/>
SELECT DISTINCT ?work ?creationYear
WHERE {
  GRAPH apsearch: {
    ?work a apsearch:Work ;
          wdt:P31 wd:Q3302947 ;
          wdt:P123 ?publisher ;
          wdt:P571 ?creationYear .
    ?publisher wdt:P2888 wd:Q219989 .
  }
}
ORDER BY ?creationYear ?work
LIMIT 100
```

The audio filter excludes unclassified works, including the early records returned
by the old query. This is why the new question says **explicitly classified**.
The schema notes retain this completeness caveat and now explain the lost date ranges.

Seven related questions (#147, #148, #164–168) used the same unsupported field-recording
wording. Their questions now describe dated archive entries, work counts, content
types or licenses. Their matching/counting logic is unchanged; output aliases were
renamed where they also overclaimed recording status. Existing year bounds are now
explicit in the questions. These are scope corrections, not a new live validation
of those complete queries or evidence of historical music-making trends.

**Separate data anomaly:** the record
[“Sudan Situation”](https://apsearch.org/record/d9f3f3f7131bed76a35ee736d67ba1b810da415b23e1c92dd3f36dcde271912e)
has `P571 "9009"^^xsd:gYear` in the live graph. Its source URL is
[the archived content handle](https://hdl.loc.gov/hdl:2196/00-0000-0000-0008-9FE0-C).
The intended year was not verified, so no replacement year or silent date cutoff
was invented. Raw responses and the manual-review query remain local and ignored.

The existing pairs are used as model context, so scores on those pairs are
regression checks, not held-out accuracy. A later accuracy experiment needs new
questions or whole question families excluded from both static few-shot and RAG
context; holding out only an exact sentence is insufficient if near-duplicates remain.

Corpus and RAG metadata corrections take effect after the service's normal startup
reseeds its example collection. No running collection was modified in this pass.

## What the five UI questions reveal

| UI question | Free data check and expected interpretation |
| --- | --- |
| Concerts versus recordings by decade | Both graphs contain the relevant date properties. Counts describe archive coverage; they do not establish a historical shift from live to recorded music or prove concerts were public. The probe does not compute the full comparison. |
| Works by Clara Schumann | The related-person path returns rows, but sample work URLs include Beethoven and Robert Schumann. This path cannot establish composition. Clara's QID was checked against Wikidata: `Q132232`. A complete answer needs role evidence. |
| Detmold works staged in the 1830s | The creation-date probe returns rows with mixed date precision. `P571` is not evidence that a work was staged in that decade. |
| Arabic vocal field recordings before 1950 | The explicit audio-type/date probe returns no rows. A follow-up count found 128 pre-1950 works, all carrying only generic `Q17537576` typing. Language, vocal status and field-recording status are not structured in the imported feed. Do not remove those conditions and present generic records as verified recordings. |
| Composers who performed and were born in Vienna | Local related-person/QID candidates exist. The probe does not verify birthplace. Related-person links do not prove composer/performer roles, and unavailable external birthplace data must not produce an unfiltered local answer. |

The probes are defined in [reliability_cases.json](reliability_cases.json);
`check_reliability_data.py` writes their results to a local output file.
The APSearch follow-up was:

```sparql
SELECT ?type (COUNT(DISTINCT ?work) AS ?n) WHERE {
  GRAPH <https://linkedmusic.ca/graphs/ckg-apsearch/> {
    ?work a <https://linkedmusic.ca/graphs/ckg-apsearch/Work> ;
      <http://www.wikidata.org/prop/direct/P571> ?date .
    FILTER(STR(?date) < "1950")
    OPTIONAL { ?work <http://www.wikidata.org/prop/direct/P31> ?type }
  }
} GROUP BY ?type LIMIT 10
```

These are useful presentation examples of why preserving relation meanings matters.
The five UI questions have not been rewritten to make them easier to answer.

## Small linking audit

In a convenience sample of **30 Detmold Person links**, all 30 source GND/VIAF IDs
appeared on their linked Wikidata items, and 14 had matching MusicBrainz artists.
This establishes authority-ID agreement in that sample, not population accuracy.
From the repository root, use
`llm-service/.venv/bin/python eval/audit_links.py --limit 30 --output eval/audits/links.json`
to collect a new local sample.

With `--qids`, the sample limit is ignored: all requested QIDs must be returned,
and the audit accepts at most 50 links. It fetches at most 51 rows to detect overflow.
Missing targets or overflow fail before authority lookups or report writing;
split an oversized request into smaller target sets.

A separate follow-up checked two suspicious records encountered in an earlier
five-row inspection:

| Locally typed Person | Wikidata target | Finding |
| --- | --- | --- |
| `https://d-nb.info/gnd/4655598-5` | [Q972277](https://www.wikidata.org/wiki/Q972277), *Les deux journées* | Wikidata describes an opera. |
| `https://d-nb.info/gnd/4658394-4` | [Q3781653](https://www.wikidata.org/wiki/Q3781653), *Una cosa rara* | Wikidata describes an opera. |

The original GND IDs were not confirmed on these Wikidata items by the exact-ID
check. Redirects/authority merges need investigation before calling the links
themselves incorrect. The local Person-versus-work mismatch is clear enough to
flag for source/converter review. No RDF or crosswalk was changed.
Use the targeted command below to repeat this check.

The sample and targeted cases have different selection methods. Do not combine
them into an estimated error rate. A next small data task is tracing these two
authority records through CKG ingestion before defining a correction.

## Validation

The combined change set was checked on 16 September 2026. Each PR description
lists its own branch-specific checks.

- 153 Python tests pass, with network access blocked.
- 13 frontend tests pass.
- TypeScript checking, ESLint, Black and `git diff --check` pass.

On 17 September, PR #48 was rebased onto main after #45 merged. Its **168 backend
tests** pass with network access blocked, including regressions for unscoped schema
terms, complete 31–50-QID targeted audits, sample limits, missing targets and overflow.
Missing or oversized target sets preserve any existing report. Corpus checks now
validate default-graph and variable-graph terms against all documented local schemas;
fixed-graph checks retain their graph-specific rules and external SERVICE stays separate.
Black and diff checks pass. This review used mocked endpoints; no live queries or
paid model calls were needed.

These checks cover application behavior and static corpus validity. They do not
measure Qwen answer quality or latency, and the UI has not had a browser-based
visual review in this pass.

## Reproduce without a model

From the repository root, write generated output to the ignored directory:

```bash
(cd llm-service && .venv/bin/python -m pytest tests/test_examples.py -q)
llm-service/.venv/bin/python eval/check_reliability_data.py --output eval/audits/ui-data.json
llm-service/.venv/bin/python eval/audit_links.py --limit 30 --output eval/audits/links.json
llm-service/.venv/bin/python eval/audit_links.py --qids Q972277 Q3781653 --output eval/audits/targeted-links.json
```

The scripts create the output directory as needed. Generated files are not required
for a fresh checkout or CI.

Only the first command is offline. The other commands make bounded, read-only requests
to public services; they never import the model factory or call Qwen.

Before a Qwen comparison, agree on the question(s), maximum calls including retries,
and the runtime configuration. Compare preserved constraints, answer evidence,
limitations and model calls, as well as latency. The local full-corpus path differs
from production's RAG selection, so results from the two should be labelled separately.
