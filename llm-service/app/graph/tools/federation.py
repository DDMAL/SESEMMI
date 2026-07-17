"""Helpers for reasoning about federated (SERVICE) SPARQL queries.

Dependency-free (only ``re``) so it can be imported from the executor, the validator, and
the judge without risking an import cycle. Brace matching is best-effort and does not account
for braces inside string literals — callers treat every result as advisory and fall back
gracefully on a parse miss.
"""

import re

# A federated call to public Wikidata. Virtuoso wraps a failed SERVICE call in an SPARQL_REXEC
# error that names the remote endpoint; a 429/5xx from public WDQS (or a SERVICE timeout) is a
# transient, external failure — rewriting our query cannot fix it.
_EXTERNAL_MARKER = re.compile(
    r"SPARQL_REXEC|query\.wikidata\.org|wikidata\.org/sparql", re.IGNORECASE
)
_TRANSIENT = re.compile(
    r"\b(429|50\d)\b|too many requests|timed?\s*out|timeout", re.IGNORECASE
)
_WD_SERVICE = re.compile(r"SERVICE\s+<[^>]*wikidata[^>]*>", re.IGNORECASE)
_SERVICE_KW = re.compile(r"\bSERVICE\b", re.IGNORECASE)


def has_wikidata_service(sparql: str) -> bool:
    """True if the query federates to a Wikidata endpoint via SERVICE."""
    return bool(_WD_SERVICE.search(sparql))


def classify_execution_error(query: str, error_text: str) -> str:
    """Classify a failed execution so the pipeline can route it.

    "external_service" — a federated SERVICE call to an external endpoint failed transiently
    (429 / 5xx / timeout); repairing the local query is futile. "query_fault" — a fault in the
    query itself (syntax, Virtuoso SP031, missing variable); a repair may fix it.
    """
    text = error_text or ""
    if _EXTERNAL_MARKER.search(text) and _TRANSIENT.search(text):
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
