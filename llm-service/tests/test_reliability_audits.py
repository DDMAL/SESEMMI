"""Exercise the link-audit CLI with mocked endpoints and temporary reports."""

import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


@pytest.fixture
def link_audit(monkeypatch):
    """Load the standalone tool and model the endpoint's row-limit behavior."""
    path = Path(__file__).resolve().parents[2] / "eval/audit_links.py"
    spec = importlib.util.spec_from_file_location("audit_links", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state = {"bindings": [], "authority_requests": []}

    def sparql(query):
        if "graphs/musicbrainz/" in query:
            return []
        limit = re.search(r"LIMIT\s+(\d+)", query)
        return state["bindings"][: int(limit.group(1))] if limit else state["bindings"]

    def get_json(url, params):
        state["authority_requests"].append(params["ids"])
        return {"entities": {qid: {} for qid in params["ids"].split("|")}}

    monkeypatch.setattr(module, "sparql", sparql)
    monkeypatch.setattr(module, "get_json", get_json)
    return module, state


def bindings_for(qids):
    """Build distinct source links, including multiple links to the same QID."""
    return [
        {
            "person": {"value": f"https://d-nb.info/gnd/{index}"},
            "qid": {"value": f"http://www.wikidata.org/entity/{qid}"},
        }
        for index, qid in enumerate(qids)
    ]


@pytest.mark.parametrize("count", [31, 50])
def test_targeted_audit_includes_every_qid_above_default_sample_limit(
    link_audit, monkeypatch, tmp_path, count
):
    module, state = link_audit
    qids = [f"Q{index}" for index in range(1, count + 1)]
    state["bindings"] = bindings_for(qids)
    output = tmp_path / "targeted.json"
    monkeypatch.setattr(
        sys, "argv", ["audit_links.py", "--output", str(output), "--qids", *qids]
    )

    module.main()

    report = json.loads(output.read_text())
    assert report["count"] == count
    assert {link["qid"] for link in report["links"]} == set(qids)
    assert len(state["authority_requests"]) == 1
    assert set(state["authority_requests"][0].split("|")) == set(qids)


def test_convenience_sample_respects_limit(link_audit, monkeypatch, tmp_path):
    module, state = link_audit
    state["bindings"] = bindings_for(["Q1", "Q2", "Q3"])
    output = tmp_path / "sample.json"
    monkeypatch.setattr(
        sys, "argv", ["audit_links.py", "--output", str(output), "--limit", "2"]
    )

    module.main()

    assert json.loads(output.read_text())["count"] == 2
    assert state["authority_requests"] == ["Q1|Q2"]


@pytest.mark.parametrize(
    "requested,returned,error",
    [
        (["Q1", "Q2"], ["Q1"], "did not return requested QIDs: Q2"),
        (["Q1"], [], "did not return requested QIDs: Q1"),
        (["Q1"], ["Q1"] * 51, "exceeds 50 links"),
    ],
)
def test_incomplete_targeted_audit_preserves_report_and_skips_authority_lookups(
    link_audit, monkeypatch, tmp_path, requested, returned, error
):
    module, state = link_audit
    state["bindings"] = bindings_for(returned)
    output = tmp_path / "existing.json"
    output.write_text("previous report\n")
    monkeypatch.setattr(
        sys, "argv", ["audit_links.py", "--output", str(output), "--qids", *requested]
    )

    with pytest.raises(ValueError, match=error):
        module.main()

    assert state["authority_requests"] == []
    assert output.read_text() == "previous report\n"
