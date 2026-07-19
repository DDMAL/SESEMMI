"""Routing tests for the conditional edges in builder.py."""

from app.graph.builder import after_judge, after_validate


def test_after_judge_external_service_does_not_reroute():
    """A persistent external-SERVICE failure ends the run — it must not loop back to intake.

    Layer 3 in judge degrades such a failure and clears execution_error, so by the time the
    router sees the state there is no error to repair and it finalizes."""
    state = {
        "judge_feedback": None,
        "execution_error": None,  # judge's _degrade_external_service cleared it
        "error_kind": None,
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
