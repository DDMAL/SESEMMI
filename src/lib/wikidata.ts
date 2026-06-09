// Client-side Wikidata resolution for the Results table.
// The Wikidata Action API supports anonymous CORS (origin=*), so we can fetch
// labels/descriptions/claims directly from the browser. Results are cached in
// module-level maps so repeated cells/queries don't refetch.

const API = "https://www.wikidata.org/w/api.php";

const labelCache = new Map<string, string>();
const entityCache = new Map<string, EntityDetail>();

export interface EntityFact {
  prop: string; // human label of the property, e.g. "occupation"
  value: string; // resolved value (entity label or formatted literal)
}

export interface EntityDetail {
  qid: string;
  label: string;
  description: string;
  facts: EntityFact[];
  url: string;
}

/** Extract a Wikidata QID from a URI, or null if it isn't a Wikidata entity. */
export function extractQid(uri: string): string | null {
  const m = uri.match(/wikidata\.org\/(?:entity|wiki)\/(Q\d+)/i);
  return m ? m[1] : null;
}

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

/** Batch-resolve QIDs to English labels (chunked ≤50/request), using the cache. */
export async function fetchLabels(qids: string[]): Promise<Record<string, string>> {
  const unique = [...new Set(qids)].filter((q) => !labelCache.has(q));

  await Promise.all(
    chunk(unique, 50).map(async (ids) => {
      const params = new URLSearchParams({
        action: "wbgetentities",
        props: "labels",
        languages: "en",
        format: "json",
        origin: "*",
        ids: ids.join("|"),
      });
      try {
        const res = await fetch(`${API}?${params}`);
        if (!res.ok) return;
        const data = await res.json();
        for (const id of ids) {
          const label = data?.entities?.[id]?.labels?.en?.value;
          labelCache.set(id, label ?? id);
        }
      } catch {
        // Network/parse failure — leave uncached so a later attempt can retry.
      }
    }),
  );

  const out: Record<string, string> = {};
  for (const q of qids) out[q] = labelCache.get(q) ?? q;
  return out;
}

// Curated, high-signal properties to surface in the detail tab.
const FACT_PROPS: { id: string; label: string }[] = [
  { id: "P106", label: "occupation" },
  { id: "P569", label: "born" },
  { id: "P570", label: "died" },
  { id: "P19", label: "birthplace" },
  { id: "P27", label: "citizenship" },
  { id: "P136", label: "genre" },
];

function formatTime(value: string): string {
  // Wikidata time values look like "+1685-03-31T00:00:00Z".
  const m = value.match(/^[+-](\d{4})-(\d{2})-(\d{2})/);
  if (!m) return value.replace(/^\+/, "");
  const [, y, mo, d] = m;
  if (mo === "00") return y;
  if (d === "00") return `${y}-${mo}`;
  return `${y}-${mo}-${d}`;
}

/** Fetch a single entity's label, description, and a curated set of facts. */
export async function fetchEntity(qid: string): Promise<EntityDetail> {
  const cached = entityCache.get(qid);
  if (cached) return cached;

  const params = new URLSearchParams({
    action: "wbgetentities",
    props: "labels|descriptions|claims",
    languages: "en",
    format: "json",
    origin: "*",
    ids: qid,
  });

  const res = await fetch(`${API}?${params}`);
  if (!res.ok) throw new Error(`Wikidata error ${res.status}`);
  const data = await res.json();
  const ent = data?.entities?.[qid];

  const label: string = ent?.labels?.en?.value ?? qid;
  const description: string = ent?.descriptions?.en?.value ?? "";
  const claims = ent?.claims ?? {};

  // First pass: collect raw fact values; gather entity-valued QIDs to resolve.
  const raw: { label: string; value: string; refQid?: string }[] = [];
  const refQids: string[] = [];
  for (const { id, label: propLabel } of FACT_PROPS) {
    const statements = claims[id];
    if (!Array.isArray(statements) || statements.length === 0) continue;
    const snak = statements[0]?.mainsnak?.datavalue;
    if (!snak) continue;
    if (snak.type === "wikibase-entityid" && snak.value?.id) {
      const ref = snak.value.id as string;
      refQids.push(ref);
      raw.push({ label: propLabel, value: ref, refQid: ref });
    } else if (snak.type === "time" && snak.value?.time) {
      raw.push({ label: propLabel, value: formatTime(snak.value.time) });
    } else if (snak.type === "string") {
      raw.push({ label: propLabel, value: String(snak.value) });
    }
  }

  const refLabels = refQids.length ? await fetchLabels(refQids) : {};
  const facts: EntityFact[] = raw.map((r) => ({
    prop: r.label,
    value: r.refQid ? (refLabels[r.refQid] ?? r.value) : r.value,
  }));

  const detail: EntityDetail = {
    qid,
    label,
    description,
    facts,
    url: `https://www.wikidata.org/wiki/${qid}`,
  };
  entityCache.set(qid, detail);
  labelCache.set(qid, label);
  return detail;
}
