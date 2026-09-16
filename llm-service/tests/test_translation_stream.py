"""The streaming endpoint must expose the same caveats as /translate."""

import json
from unittest.mock import patch

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
