"""The streaming endpoint must expose the same caveats as /translate."""

import json
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from app.main import TranslateRequest, translate_stream


async def test_stream_includes_final_assumptions():
    class Graph:
        async def astream_events(self, *args, **kwargs):
            yield {
                "event": "on_chain_end",
                "name": "generate",
                "data": {"output": {"sparql": "SELECT ?work WHERE {}"}},
            }
            yield {
                "event": "on_chain_end",
                "name": "judge",
                "data": {
                    "output": {
                        "confidence": "medium",
                        "assumptions": [
                            "Matching titles do not establish recording identity."
                        ],
                    }
                },
            }

    with patch("app.main.build_graph", return_value=Graph()):
        response = await translate_stream(
            TranslateRequest(query="Find shared recordings")
        )
        events = [event async for event in response.body_iterator]
    final = next(event for event in events if event.startswith("event: done\n"))
    data = json.loads(final.split("data: ", 1)[1])
    assert data["assumptions"] == [
        "Matching titles do not establish recording identity."
    ]
    assert data["confidence"] == "medium"


@pytest.mark.parametrize(
    "final_step, final_assumptions",
    [("judge", ["Current limitation"]), ("judge", []), ("validate", [])],
)
async def test_stream_replaces_assessment_after_regeneration(
    final_step: str, final_assumptions: list[str]
) -> None:
    class Graph:
        async def astream_events(
            self, *args: object, **kwargs: object
        ) -> AsyncIterator[dict]:
            for name, output in [
                ("generate", {"sparql": "SELECT ?old WHERE {}"}),
                (
                    "judge",
                    {"confidence": "medium", "assumptions": ["Previous limitation"]},
                ),
                ("generate", {"sparql": "SELECT ?new WHERE {}", "assumptions": []}),
                (final_step, {"confidence": "low", "assumptions": final_assumptions}),
            ]:
                yield {
                    "event": "on_chain_end",
                    "name": name,
                    "data": {"output": output},
                }

    with patch("app.main.build_graph", return_value=Graph()):
        response = await translate_stream(TranslateRequest(query="Find recordings"))
        events = [event async for event in response.body_iterator]

    final = next(event for event in events if event.startswith("event: done\n"))
    assert json.loads(final.split("data: ", 1)[1]) == {
        "sparql": "SELECT ?new WHERE {}",
        "confidence": "low",
        "assumptions": final_assumptions,
    }


async def test_failed_stream_does_not_publish_intermediate_assessment() -> None:
    class Graph:
        async def astream_events(
            self, *args: object, **kwargs: object
        ) -> AsyncIterator[dict]:
            yield {
                "event": "on_chain_end",
                "name": "judge",
                "data": {"output": {"assumptions": ["Intermediate limitation"]}},
            }
            raise RuntimeError("Repair failed")

    with patch("app.main.build_graph", return_value=Graph()):
        response = await translate_stream(TranslateRequest(query="Find recordings"))
        events = [event async for event in response.body_iterator]

    assert not any(event.startswith("event: done\n") for event in events)
    assert json.loads(events[-1].split("data: ", 1)[1]) == {"message": "Repair failed"}
