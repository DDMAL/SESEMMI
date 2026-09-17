from typing import TypedDict


class GraphState(TypedDict, total=False):
    # Inputs
    user_query: str

    # Intake
    intents: list[str]  # e.g. ["lookup"] or ["intersection", "aggregation"]
    target_graphs: list[str]  # e.g. ["diamm", "musicbrainz"]
    needs_federation: bool
    entity_contexts: dict[
        str, str
    ]  # e.g. {"Charlie Parker": "American jazz saxophonist"}

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
    # "external_service" (a federated call failed — stop without dropping constraints) |
    # "query_fault" (a fault in the query itself — a repair may help) | None
    error_kind: str | None
    result_count: int
    results: dict | None

    # Semantic judge (judge node, optional)
    # None means no repair; even an empty reason requests one.
    judge_feedback: str | None

    # Loop control
    repair_count: int
    max_repairs: int

    # Output
    confidence: str  # high | medium | low
    assumptions: list[str]
