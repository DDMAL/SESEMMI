from unittest.mock import AsyncMock, patch

from app.graph.nodes.retrieve import _get_needed_ontologies, _NeededNodes
from app.graph.schema_corpus import ONTOLOGY_CHUNKS


async def test_unknown_selected_classes_do_not_erase_schema():
    model = AsyncMock()
    model.ainvoke.return_value = _NeededNodes(nodes=["diamm:ImaginaryClass"])
    with patch("app.graph.nodes.retrieve.get_structured_model", return_value=model):
        result = await _get_needed_ontologies("Find compositions", ["diamm"])
    assert result["diamm"] == ONTOLOGY_CHUNKS["diamm"]
