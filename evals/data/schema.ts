/**
 * Benchmark entry schema for the SESEMMI NL→SPARQL evaluation framework.
 *
 * Each entry represents a single natural-language question paired with a
 * verified gold-standard SPARQL query. Entries are split into three strict
 * partitions: TRAIN (few-shot pool), DEV (prompt tuning), TEST (held-out).
 */

// ---------------------------------------------------------------------------
// Categories — mapped from the 4 LinkedMusic challenges + 2 structural types
// ---------------------------------------------------------------------------

export type Category =
  | "single_graph_lookup" // Challenge 1: basic entity retrieval within one graph
  | "aggregation" // Challenge 2: COUNT, GROUP BY, DISTINCT, ORDER BY, HAVING
  | "federated" // Challenge 3: SERVICE block to Wikidata
  | "cross_database" // Challenge 4: query spans 2+ LinkedMusic graphs
  | "string_matching" // CONTAINS, REGEX, LCASE filters
  | "negation_optional"; // OPTIONAL, FILTER NOT EXISTS, MINUS

export type Difficulty = "easy" | "medium" | "hard";

export type Dataset = "train" | "dev" | "test";

// ---------------------------------------------------------------------------
// The 7 LinkedMusic databases
// ---------------------------------------------------------------------------

export type Database =
  | "cantusdb"
  | "diamm"
  | "dig-that-lick"
  | "thesession"
  | "theglobaljukebox"
  | "musicbrainz"
  | "rism";

// ---------------------------------------------------------------------------
// Benchmark entry
// ---------------------------------------------------------------------------

export interface BenchmarkEntry {
  /** Unique identifier, e.g. "dev-001", "test-012", "train-003" */
  id: string;

  /** Which dataset partition this entry belongs to */
  dataset: Dataset;

  /** Query category (maps to LinkedMusic challenge type) */
  category: Category;

  /** Estimated difficulty for the LLM */
  difficulty: Difficulty;

  /** The natural-language question a user would ask */
  nl: string;

  /** Gold-standard SPARQL query — must execute without error on Virtuoso */
  gold_sparql: string;

  /**
   * Snapshot of sorted query results (order-independent comparison).
   * When null, the eval runner executes the gold query live against Virtuoso.
   * Store as null for large/volatile result sets.
   */
  gold_result_json: Record<string, unknown>[] | null;

  /** Which LinkedMusic databases the query touches */
  databases: Database[];

  /** Whether the query uses a SERVICE block to an external SPARQL endpoint */
  requires_federation: boolean;

  /** Whether the query requires resolving a Wikidata Q-ID for an entity */
  requires_qid: boolean;

  /**
   * Optional annotator notes — useful for debugging eval failures,
   * documenting Q-ID sources, or flagging known issues.
   */
  notes?: string;
}

// ---------------------------------------------------------------------------
// Dataset file type (what train.json / dev.json / test.json contain)
// ---------------------------------------------------------------------------

export type BenchmarkDataset = BenchmarkEntry[];
