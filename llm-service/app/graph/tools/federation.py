"""Helpers for reasoning about federated (SERVICE) SPARQL queries.

Dependency-free (only ``re``) so it can be imported from the executor, the validator, and
the judge without risking an import cycle. Brace matching is best-effort and does not account
for braces inside string literals — callers treat every result as advisory and fall back
gracefully on a parse miss.
"""

import re

# A failure of the federated SERVICE call to public Wikidata. Virtuoso reports it with an
# SPARQL_REXEC wrapper that names the remote endpoint and echoes the remote HTTP status. We don't
# distinguish 429 / 5xx / timeout — all are external and degrade the same way — so "did the remote
# SERVICE fail?" is the only question. We match only evidence Virtuoso *adds* to describe a remote
# failure, NOT the bare endpoint URL: Virtuoso echoes the offending query (which always contains
# `SERVICE <…wikidata…>`) in many local compile errors (e.g. SP031), so keying on the URL would
# misread a repairable local fault as an unfixable remote one.
_EXTERNAL_MARKER = re.compile(
    r"SPARQL_REXEC|remote endpoint|returned\s+HTTP|too many requests", re.IGNORECASE
)
_WD_SERVICE = re.compile(r"SERVICE\s+<[^>]*wikidata[^>]*>", re.IGNORECASE)
_SERVICE_KW = re.compile(r"\bSERVICE\b", re.IGNORECASE)


def has_wikidata_service(sparql: str) -> bool:
    """True if the query federates to a Wikidata endpoint via SERVICE."""
    return bool(_WD_SERVICE.search(sparql))


def classify_execution_error(query: str, error_text: str) -> str:
    """Classify a failed execution so the pipeline can route it.

    "external_service" — the federated SERVICE call to Wikidata failed (a SPARQL_REXEC wrapping a
    remote error, or a timeout on a query that federates); the remote call can't be fixed by
    rewriting, so the pipeline degrades to the local part. "query_fault" — a fault in the query
    itself (syntax, Virtuoso SP031, missing variable); a repair may fix it.
    """
    text = error_text or ""
    if _EXTERNAL_MARKER.search(text):
        return "external_service"
    low = text.lower()
    if ("timeout" in low or "timed out" in low) and has_wikidata_service(query):
        return "external_service"
    return "query_fault"


def _match_brace(sparql: str, open_idx: int) -> int:
    """Index of the '}' matching the '{' at open_idx (or len(sparql) if unbalanced)."""
    depth = 0
    for j in range(open_idx, len(sparql)):
        if sparql[j] == "{":
            depth += 1
        elif sparql[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return len(sparql)


def service_block_spans(sparql: str) -> list[tuple[int, int]]:
    """(start, end) char spans of each SERVICE …{ … } block — start at the SERVICE keyword,
    end just past its matching closing brace. Nested SERVICE blocks are reported as-is.
    """
    spans: list[tuple[int, int]] = []
    for m in _SERVICE_KW.finditer(sparql):
        brace = sparql.find("{", m.end())
        if brace == -1:
            continue
        spans.append((m.start(), _match_brace(sparql, brace) + 1))
    return spans


def strip_service_blocks(sparql: str) -> str:
    """Remove every SERVICE …{ … } block, returning the local-only remainder. Used to salvage
    the local part of a federated query whose external SERVICE call failed."""
    out: list[str] = []
    i = 0
    while True:
        m = _SERVICE_KW.search(sparql, i)
        if not m:
            out.append(sparql[i:])
            break
        out.append(sparql[i : m.start()])
        brace = sparql.find("{", m.end())
        if brace == -1:
            out.append(sparql[m.start() :])
            break
        i = _match_brace(sparql, brace) + 1
    return "".join(out)


def has_local_pattern(sparql: str) -> bool:
    """True if a graph pattern survives once SERVICE blocks are stripped — i.e. there is a local
    subquery worth running on its own. Detects a variable in the WHERE body (after the opening
    brace, so the SELECT projection doesn't count), which reads as absent for a query whose only
    content was the SERVICE block. More robust than a bare ``"GRAPH" in ...`` check, which misses
    a local pattern over the default graph."""
    body = strip_service_blocks(sparql)
    brace = body.find("{")
    return bool(re.search(r"[?$][A-Za-z_]", body[brace:] if brace != -1 else body))
