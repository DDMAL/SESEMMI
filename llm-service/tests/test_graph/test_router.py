"""Routing tests for the conditional edges in builder.py."""

from app.graph.builder import after_judge, after_validate


def test_after_judge_external_service_does_not_reroute():
    """An external outage ends the run even if stale judge feedback remains."""
    state = {
        "judge_feedback": "Try again",
        "execution_error": "Wikidata HTTP 429",
        "error_kind": "external_service",
        "repair_count": 0,
        "max_repairs": 3,
    }
    assert after_judge(state) == "__end__"


def test_after_judge_query_fault_reroutes_to_intake():
    """A genuine query fault with repairs remaining still routes back to intake."""
    state = {
        "judge_feedback": None,
        "execution_error": "HTTP 500: Virtuoso SP031 variable not bound",
        "error_kind": "query_fault",
        "repair_count": 0,
        "max_repairs": 3,
    }
    assert after_judge(state) == "intake"


def test_after_judge_query_fault_exhausted_ends():
    state = {
        "judge_feedback": None,
        "execution_error": "HTTP 500: Virtuoso SP031 variable not bound",
        "error_kind": "query_fault",
        "repair_count": 3,
        "max_repairs": 3,
    }
    assert after_judge(state) == "__end__"


def test_after_judge_judge_feedback_reroutes():
    state = {"judge_feedback": "wrong columns", "repair_count": 0, "max_repairs": 3}
    assert after_judge(state) == "intake"


def test_after_judge_clean_success_ends():
    state = {
        "judge_feedback": None,
        "execution_error": None,
        "error_kind": None,
        "repair_count": 0,
        "max_repairs": 3,
    }
    assert after_judge(state) == "__end__"


def test_after_judge_feedback_cannot_exceed_repair_budget():
    assert (
        after_judge({"judge_feedback": "retry", "repair_count": 3, "max_repairs": 3})
        == "__end__"
    )


def test_after_judge_external_error_is_preserved_without_retry():
    assert (
        after_judge(
            {
                "execution_error": "Wikidata HTTP 429",
                "error_kind": "external_service",
                "repair_count": 0,
            }
        )
        == "__end__"
    )


def test_after_validate_valid_goes_to_execute():
    assert after_validate({"is_valid": True}) == "execute"


def test_after_validate_invalid_with_repairs_regenerates():
    assert (
        after_validate({"is_valid": False, "repair_count": 0, "max_repairs": 3})
        == "generate"
    )


def test_after_validate_invalid_exhausted_ends():
    assert (
        after_validate({"is_valid": False, "repair_count": 3, "max_repairs": 3})
        == "__end__"
    )
