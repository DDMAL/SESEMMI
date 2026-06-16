import { Decoration, EditorView, ViewPlugin, hoverTooltip } from "@codemirror/view";
import type { DecorationSet } from "@codemirror/view";
import { StateEffect, StateField } from "@codemirror/state";

interface KeywordInfo {
  label: string;
  description: string;
}

const KEYWORD_INFO: Record<string, KeywordInfo> = {
  SELECT: { label: "SELECT", description: "Specifies which variables appear in the results." },
  DISTINCT: { label: "DISTINCT", description: "Removes duplicate rows from the results." },
  REDUCED: { label: "REDUCED", description: "May remove duplicates (implementation-defined)." },
  WHERE: {
    label: "WHERE",
    description: "Defines the graph pattern conditions that must be satisfied.",
  },
  FILTER: {
    label: "FILTER",
    description: "Applies a boolean condition to keep only matching results.",
  },
  OPTIONAL: {
    label: "OPTIONAL",
    description:
      "Makes a sub-pattern optional — results are kept even when this part has no match.",
  },
  UNION: {
    label: "UNION",
    description: "Combines results from two alternative graph patterns.",
  },
  MINUS: { label: "MINUS", description: "Excludes solutions that also satisfy this pattern." },
  GRAPH: { label: "GRAPH", description: "Restricts the pattern to a specific named graph." },
  SERVICE: {
    label: "SERVICE",
    description: "Delegates part of the query to a remote SPARQL endpoint.",
  },
  BIND: {
    label: "BIND",
    description: "Assigns the result of an expression to a new variable.",
  },
  VALUES: {
    label: "VALUES",
    description: "Provides inline data as a set of variable bindings.",
  },
  GROUP: {
    label: "GROUP BY",
    description: "Groups results by the specified variable(s) for aggregation.",
  },
  ORDER: { label: "ORDER BY", description: "Sorts the results by one or more expressions." },
  HAVING: {
    label: "HAVING",
    description: "Filters groups after aggregation — like FILTER but for GROUP BY.",
  },
  LIMIT: { label: "LIMIT", description: "Restricts the maximum number of results returned." },
  OFFSET: { label: "OFFSET", description: "Skips the first N results before returning the rest." },
  PREFIX: {
    label: "PREFIX",
    description: "Declares a namespace prefix shortcut (e.g. PREFIX rdf: <...>).",
  },
  BASE: { label: "BASE", description: "Sets the base IRI for resolving relative IRIs." },
  ASK: {
    label: "ASK",
    description: "Returns true or false — whether the pattern has any matches.",
  },
  CONSTRUCT: {
    label: "CONSTRUCT",
    description: "Builds a new RDF graph using a template applied to query matches.",
  },
  DESCRIBE: {
    label: "DESCRIBE",
    description: "Returns an RDF description of the matched resources.",
  },
  FROM: { label: "FROM", description: "Specifies the dataset (graph) to query against." },
  EXISTS: {
    label: "EXISTS",
    description: "Tests whether a pattern has at least one match (used inside FILTER).",
  },
  NOT: {
    label: "NOT EXISTS / NOT IN",
    description: "Tests that a pattern has no matches, or that a value is absent from a list.",
  },
  IN: { label: "IN", description: "Tests whether a value is one of the listed values." },
  ASC: { label: "ASC", description: "Sorts results in ascending order (used with ORDER BY)." },
  DESC: {
    label: "DESC",
    description: "Sorts results in descending order (used with ORDER BY).",
  },
  COUNT: { label: "COUNT", description: "Aggregate: counts the number of matching rows." },
  SUM: { label: "SUM", description: "Aggregate: adds up numeric values across the group." },
  AVG: {
    label: "AVG",
    description: "Aggregate: calculates the average of numeric values.",
  },
  MIN: { label: "MIN", description: "Aggregate: returns the smallest value in the group." },
  MAX: { label: "MAX", description: "Aggregate: returns the largest value in the group." },
  GROUP_CONCAT: {
    label: "GROUP_CONCAT",
    description: "Aggregate: concatenates values within a group into a single string.",
  },
  SAMPLE: {
    label: "SAMPLE",
    description: "Aggregate: returns an arbitrary value from the group.",
  },
  COALESCE: {
    label: "COALESCE",
    description: "Returns the first defined (non-error) value from a list.",
  },
  IF: { label: "IF", description: "Returns one of two values based on a boolean condition." },
  BOUND: {
    label: "BOUND",
    description: "Returns true if the variable is currently bound to a value.",
  },
  ISIRI: {
    label: "ISIRI",
    description: "Returns true if the value is an IRI (resource identifier).",
  },
  ISURI: {
    label: "ISURI",
    description: "Returns true if the value is an IRI (resource identifier).",
  },
  ISBLANK: { label: "ISBLANK", description: "Returns true if the value is a blank node." },
  ISLITERAL: { label: "ISLITERAL", description: "Returns true if the value is a literal." },
  ISNUMERIC: {
    label: "ISNUMERIC",
    description: "Returns true if the value is a numeric literal.",
  },
  REGEX: { label: "REGEX", description: "Tests if a string matches a regular expression." },
  LANG: {
    label: "LANG",
    description: "Returns the language tag of a string literal (e.g. 'en', 'de').",
  },
  DATATYPE: { label: "DATATYPE", description: "Returns the datatype IRI of a literal." },
  STR: { label: "STR", description: "Converts a value to its string representation." },
  CONTAINS: {
    label: "CONTAINS",
    description: "Returns true if the string contains the given substring.",
  },
  STRSTARTS: {
    label: "STRSTARTS",
    description: "Returns true if the string starts with the given substring.",
  },
  STRENDS: {
    label: "STRENDS",
    description: "Returns true if the string ends with the given substring.",
  },
  STRLEN: { label: "STRLEN", description: "Returns the number of characters in a string." },
  UCASE: { label: "UCASE", description: "Converts a string to all uppercase." },
  LCASE: { label: "LCASE", description: "Converts a string to all lowercase." },
  SUBSTR: {
    label: "SUBSTR",
    description: "Returns a portion of a string by start position and optional length.",
  },
  REPLACE: {
    label: "REPLACE",
    description: "Replaces occurrences of a pattern within a string.",
  },
  CONCAT: { label: "CONCAT", description: "Joins multiple strings together." },
  LANGMATCHES: {
    label: "LANGMATCHES",
    description: "Tests if a language tag matches a language range.",
  },
  NOW: { label: "NOW", description: "Returns the current date and time as xsd:dateTime." },
  YEAR: { label: "YEAR", description: "Extracts the year from a date/time value." },
  MONTH: { label: "MONTH", description: "Extracts the month from a date/time value." },
  DAY: { label: "DAY", description: "Extracts the day from a date/time value." },
  ABS: {
    label: "ABS",
    description: "Returns the absolute (non-negative) value of a number.",
  },
  ROUND: { label: "ROUND", description: "Rounds a number to the nearest integer." },
  CEIL: { label: "CEIL", description: "Rounds a number up to the nearest integer." },
  FLOOR: { label: "FLOOR", description: "Rounds a number down to the nearest integer." },
  NAMED: {
    label: "NAMED",
    description: "Used with FROM NAMED to specify a named graph dataset.",
  },
  AS: {
    label: "AS",
    description: "Aliases an expression to a variable (used with BIND or in SELECT).",
  },
  SAMETERM: {
    label: "SAMETERM",
    description: "Returns true if two values are the same RDF term (identity, not value equality).",
  },
};

function getContextHint(doc: string, from: number, keyword: string): string | null {
  const after = doc.slice(from);
  switch (keyword) {
    case "SELECT": {
      const m = /^SELECT\s+(?:DISTINCT\s+|REDUCED\s+)?(\*|(?:\?[\w]+\s*)+)/i.exec(after);
      if (!m) return null;
      return m[1].trim() === "*" ? "→ all variables" : `→ ${m[1].trim().split(/\s+/).join(", ")}`;
    }
    case "LIMIT": {
      const m = /^LIMIT\s+(\d+)/i.exec(after);
      return m ? `→ ${m[1]} results` : null;
    }
    case "OFFSET": {
      const m = /^OFFSET\s+(\d+)/i.exec(after);
      return m ? `→ skip first ${m[1]}` : null;
    }
    case "ORDER": {
      const m = /^ORDER\s+BY\s+(.+?)(?=\n|LIMIT|OFFSET|$)/i.exec(after);
      if (m) return `→ ${m[1].trim().slice(0, 60)}`;
      return null;
    }
    case "GROUP": {
      const m = /^GROUP\s+BY\s+((?:\?[\w]+\s*)+)/i.exec(after);
      if (m) return `→ ${m[1].trim().split(/\s+/).join(", ")}`;
      return null;
    }
    default:
      return null;
  }
}

export interface EntityInfo {
  label: string;
  description?: string;
}

// Prefixes whose local part is a Wikidata ID (Q###/P###).
const WIKIDATA_PREFIXES = new Set([
  "wd",
  "wdt",
  "p",
  "ps",
  "pq",
  "psv",
  "pqv",
  "wdtn",
  "psn",
  "wdno",
  "wikibase",
]);

// Static namespace expansion for local-graph + standard prefixes.
const PREFIX_NAMESPACES: Record<string, { uri: string; note: string }> = {
  wd: { uri: "http://www.wikidata.org/entity/", note: "Wikidata entity" },
  wdt: { uri: "http://www.wikidata.org/prop/direct/", note: "Wikidata property" },
  rdf: { uri: "http://www.w3.org/1999/02/22-rdf-syntax-ns#", note: "RDF core vocabulary" },
  rdfs: { uri: "http://www.w3.org/2000/01/rdf-schema#", note: "RDF Schema" },
  skos: { uri: "http://www.w3.org/2004/02/skos/core#", note: "SKOS vocabulary" },
  diamm: { uri: "https://linkedmusic.ca/graphs/diamm/", note: "DIAMM — medieval music archive" },
  ts: {
    uri: "https://linkedmusic.ca/graphs/thesession/",
    note: "The Session — Irish traditional music",
  },
  mb: { uri: "https://linkedmusic.ca/graphs/musicbrainz/", note: "MusicBrainz" },
  gj: { uri: "https://linkedmusic.ca/graphs/theglobaljukebox/", note: "The Global Jukebox" },
  dtl: { uri: "https://linkedmusic.ca/graphs/dig-that-lick/", note: "Dig That Lick — jazz solos" },
  cdb: { uri: "https://linkedmusic.ca/graphs/cantusdb/", note: "Cantus Database — medieval chant" },
  rism: { uri: "https://linkedmusic.ca/graphs/rism/", note: "RISM — music manuscripts" },
  wjazzd: { uri: "https://linkedmusic.ca/graphs/wjazzd/", note: "Weimar Jazz Database" },
  simssa: { uri: "https://linkedmusic.ca/graphs/simssadb/", note: "SIMSSA DB — symbolic scores" },
  utsi: { uri: "https://linkedmusic.ca/graphs/utsi/", note: "UTSI — song index" },
  cantusindex: { uri: "https://linkedmusic.ca/graphs/cantusindex/", note: "Cantus Index" },
};

// Preloaded Wikidata labels are carried in editor state so the hover provider reads them
// synchronously (no per-hover fetch). SparqlEditor dispatches setWikidataLabels after the
// debounced /api/wikidata call resolves.
export const setWikidataLabels = StateEffect.define<Record<string, EntityInfo>>();
export const wikidataLabelsField = StateField.define<Record<string, EntityInfo>>({
  create: () => ({}),
  update(value, tr) {
    for (const e of tr.effects) if (e.is(setWikidataLabels)) return e.value;
    return value;
  },
});

const PREFIXED_NAME = /([A-Za-z_][\w-]*):([A-Za-z0-9_][\w.-]*)/g;

interface PrefixedName {
  from: number;
  to: number;
  prefix: string;
  local: string;
}

function prefixedNameAt(doc: string, pos: number): PrefixedName | null {
  // Search only the current line for performance.
  const lineStart = doc.lastIndexOf("\n", pos - 1) + 1;
  let lineEnd = doc.indexOf("\n", pos);
  if (lineEnd === -1) lineEnd = doc.length;
  const line = doc.slice(lineStart, lineEnd);
  PREFIXED_NAME.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = PREFIXED_NAME.exec(line)) !== null) {
    const from = lineStart + m.index;
    const to = from + m[0].length;
    if (pos >= from && pos <= to) return { from, to, prefix: m[1], local: m[2] };
  }
  return null;
}

/** Collect unique Wikidata IDs (Q###/P###) referenced in a SPARQL string, for preloading. */
export function extractWikidataIds(sparql: string): string[] {
  const ids = new Set<string>();
  PREFIXED_NAME.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = PREFIXED_NAME.exec(sparql)) !== null) {
    if (WIKIDATA_PREFIXES.has(m[1].toLowerCase()) && /^[QP]\d+$/.test(m[2])) ids.add(m[2]);
  }
  return [...ids];
}

function isWikidataId(pn: PrefixedName): boolean {
  return WIKIDATA_PREFIXES.has(pn.prefix.toLowerCase()) && /^[QP]\d+$/.test(pn.local);
}

/** True when a prefixed name resolves to a Wikidata ID or a known namespace. */
function hasPrefixInfo(pn: PrefixedName): boolean {
  return isWikidataId(pn) || pn.prefix.toLowerCase() in PREFIX_NAMESPACES;
}

interface ResolvedTooltip {
  title: string;
  description?: string;
  hint?: string;
}

function resolvePrefixed(
  pn: PrefixedName,
  labels: Record<string, EntityInfo>,
): ResolvedTooltip | null {
  if (isWikidataId(pn)) {
    const info = labels[pn.local];
    const kind = pn.local[0] === "Q" ? "entity" : "property";
    return {
      title: info?.label ?? `Wikidata ${kind}`,
      description: info?.description ?? (info ? undefined : "Resolving from Wikidata…"),
      hint: `${pn.prefix}:${pn.local} · Wikidata ${kind}`,
    };
  }
  const ns = PREFIX_NAMESPACES[pn.prefix.toLowerCase()];
  if (ns) {
    return { title: `${pn.prefix}:${pn.local}`, description: ns.note, hint: ns.uri };
  }
  return null;
}

const setHoverKw = StateEffect.define<{ from: number; to: number } | null>();

const hoverKwField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes);
    for (const e of tr.effects) {
      if (e.is(setHoverKw)) {
        deco = e.value
          ? Decoration.set([
              Decoration.mark({ class: "cm-sparql-kw-shine" }).range(e.value.from, e.value.to),
            ])
          : Decoration.none;
      }
    }
    return deco;
  },
  provide: (f) => EditorView.decorations.from(f),
});

const hoverKwPlugin = ViewPlugin.fromClass(
  class {
    private current: { from: number; to: number } | null = null;

    constructor(private view: EditorView) {
      view.dom.addEventListener("mousemove", this.onMove);
      view.dom.addEventListener("mouseleave", this.onLeave);
    }

    destroy() {
      this.view.dom.removeEventListener("mousemove", this.onMove);
      this.view.dom.removeEventListener("mouseleave", this.onLeave);
    }

    onMove = (e: MouseEvent) => {
      const pos = this.view.posAtCoords({ x: e.clientX, y: e.clientY });
      if (pos !== null) {
        const word = this.view.state.wordAt(pos);
        if (word) {
          const token = this.view.state.doc.sliceString(word.from, word.to).toUpperCase();
          if (KEYWORD_INFO[token]) {
            this.shine(word.from, word.to);
            return;
          }
        }
        const pn = prefixedNameAt(this.view.state.doc.toString(), pos);
        if (pn && hasPrefixInfo(pn)) {
          this.shine(pn.from, pn.to);
          return;
        }
      }
      this.clear();
    };

    private shine(from: number, to: number) {
      if (!this.current || this.current.from !== from) {
        this.current = { from, to };
        this.view.dispatch({ effects: setHoverKw.of(this.current) });
        this.view.contentDOM.style.cursor = "default";
      }
    }

    onLeave = () => this.clear();

    private clear() {
      if (this.current) {
        this.current = null;
        this.view.dispatch({ effects: setHoverKw.of(null) });
        this.view.contentDOM.style.cursor = "";
      }
    }
  },
);

export function sparqlKeywordHighlight() {
  return [hoverKwField, hoverKwPlugin];
}

function buildTooltipDom(title: string, description?: string, hint?: string) {
  const dom = document.createElement("div");
  dom.className = "cm-sparql-keyword-tooltip";

  const labelEl = document.createElement("div");
  labelEl.className = "cm-sparql-kw-label";
  labelEl.textContent = title;
  dom.appendChild(labelEl);

  if (description) {
    const descEl = document.createElement("div");
    descEl.className = "cm-sparql-kw-desc";
    descEl.textContent = description;
    dom.appendChild(descEl);
  }

  if (hint) {
    const hintEl = document.createElement("div");
    hintEl.className = "cm-sparql-kw-hint";
    hintEl.textContent = hint;
    dom.appendChild(hintEl);
  }

  return { dom };
}

export function sparqlHoverTooltip() {
  return hoverTooltip((view: EditorView, pos: number) => {
    const doc = view.state.doc.toString();

    // 1. Keyword (SELECT, WHERE, FILTER, …)
    const word = view.state.wordAt(pos);
    if (word) {
      const token = doc.slice(word.from, word.to).toUpperCase();
      const info = KEYWORD_INFO[token];
      if (info) {
        const hint = getContextHint(doc, word.from, token) ?? undefined;
        return {
          pos: word.from,
          end: word.to,
          above: true,
          create: () => buildTooltipDom(info.label, info.description, hint),
        };
      }
    }

    // 2. Prefixed name (wd:Q###, wdt:P###, diamm:Archive, …)
    const pn = prefixedNameAt(doc, pos);
    if (pn) {
      const labels = view.state.field(wikidataLabelsField, false) ?? {};
      const resolved = resolvePrefixed(pn, labels);
      if (resolved) {
        return {
          pos: pn.from,
          end: pn.to,
          above: true,
          create: () => buildTooltipDom(resolved.title, resolved.description, resolved.hint),
        };
      }
    }

    return null;
  });
}
