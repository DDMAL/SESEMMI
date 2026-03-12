from typing import TypedDict


class GraphState(TypedDict, total=False):
    # Inputs
    user_query: str

    # Intake
    intent: str  # lookup | aggregation | comparison | path | cross_graph
    target_graphs: list[str]  # e.g. ["diamm", "musicbrainz"]
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
    judge_feedback: str | None  # LLM judge's reason if results don't satisfy intent

    # Loop control
    repair_count: int
    max_repairs: int

    # Output
    confidence: str  # high | medium | low
    assumptions: list[str]
