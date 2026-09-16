"""Default schema selection for graph tests; no live planner/model is needed."""

import re
from unittest.mock import AsyncMock

import pytest

from app.graph.nodes.retrieve import _NeededNodes


@pytest.fixture(autouse=True)
def stub_schema_planner(monkeypatch):
    async def select_all(messages):
        available = re.search(
            r"<available_nodes>\s*(.*?)\s*</available_nodes>", messages[0].content, re.S
        )
        return _NeededNodes(nodes=available.group(1).split(", "))

    model = AsyncMock()
    model.ainvoke.side_effect = select_all
    monkeypatch.setattr(
        "app.graph.nodes.retrieve.get_structured_model", lambda schema: model
    )
