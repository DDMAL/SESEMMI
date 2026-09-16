#!/usr/bin/env python3
"""Bounded, read-only Detmold person-link audit. No model calls or RDF writes.

Takes at most 50 links from Virtuoso, fetches their Wikidata authority IDs/types
in one API request, and checks MusicBrainz overlap in one bounded VALUES query.
This is a convenience sample, not an estimate of overall data quality.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://virtuoso.simssa.ca/sparql"


def get_json(url, params):
    request = Request(
        url + "?" + urlencode(params),
        headers={
            "User-Agent": "SESEMMI-link-audit/1.0 (https://github.com/DDMAL/SESEMMI)"
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def sparql(query):
    return get_json(
        ENDPOINT, {"query": query, "format": "application/sparql-results+json"}
    )["results"]["bindings"]


def claim_values(entity, prop):
    values = []
    for claim in entity.get("claims", {}).get(prop, []):
        snak = claim.get("mainsnak", {})
        value = snak.get("datavalue", {}).get("value")
        if isinstance(value, dict):
            value = value.get("id")
        if value is not None:
            values.append(value)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=30, choices=range(1, 51), metavar="1..50"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--qids",
        nargs="+",
        help="Optional targeted follow-up instead of a convenience sample",
    )
    args = parser.parse_args()
    if args.qids and (
        len(args.qids) > 50 or any(not re.fullmatch(r"Q\d+", qid) for qid in args.qids)
    ):
        parser.error("--qids must contain at most 50 valid QIDs")
    values = (
        "VALUES ?qid { "
        + " ".join(f"<http://www.wikidata.org/entity/{qid}>" for qid in args.qids)
        + " }"
        if args.qids
        else ""
    )
    bindings = sparql(f"""
      SELECT ?person (SAMPLE(?name) AS ?label) ?qid WHERE {{
        {values}
        GRAPH <https://linkedmusic.ca/graphs/ckg-detmold/> {{
          ?person a <https://linkedmusic.ca/graphs/ckg-detmold/Person> ;
            <http://www.wikidata.org/prop/direct/P2888> ?qid .
          OPTIONAL {{ ?person <http://www.w3.org/2000/01/rdf-schema#label> ?name }}
        }}
      }} GROUP BY ?person ?qid LIMIT {args.limit}
    """)
    qids = sorted({row["qid"]["value"].rsplit("/", 1)[-1] for row in bindings})
    if not qids or any(not re.fullmatch(r"Q\d+", qid) for qid in qids):
        raise ValueError("Expected a nonempty sample of Wikidata QIDs")
    entities = get_json(
        "https://www.wikidata.org/w/api.php",
        {
            "action": "wbgetentities",
            "ids": "|".join(qids),
            "props": "labels|descriptions|claims",
            "languages": "en",
            "format": "json",
        },
    )["entities"]
    overlap_rows = sparql("""
      SELECT ?qid (COUNT(DISTINCT ?artist) AS ?artists) WHERE {
        VALUES ?qid { %s }
        GRAPH <https://linkedmusic.ca/graphs/musicbrainz/> {
          ?artist a <https://linkedmusic.ca/graphs/musicbrainz/Artist> ;
            <http://www.wikidata.org/prop/direct/P2888> ?qid .
        }
      } GROUP BY ?qid
    """ % " ".join(f"<http://www.wikidata.org/entity/{qid}>" for qid in qids))
    overlap = {
        row["qid"]["value"].rsplit("/", 1)[-1]: int(row["artists"]["value"])
        for row in overlap_rows
    }
    rows = []
    for binding in bindings:
        source = binding["person"]["value"]
        qid = binding["qid"]["value"].rsplit("/", 1)[-1]
        entity = entities[qid]
        prop = (
            "P227"
            if "d-nb.info/gnd/" in source
            else "P214" if "viaf.org/viaf/" in source else None
        )
        source_id = source.rstrip("/").rsplit("/", 1)[-1]
        types = claim_values(entity, "P31")
        authority_match = source_id in claim_values(entity, prop) if prop else None
        flags = []
        if authority_match is not True:
            flags.append("authority_id_not_confirmed")
        if "Q5" not in types:
            flags.append("local_person_not_marked_human_on_wikidata")
        rows.append(
            {
                "source_uri": source,
                "source_label": binding.get("label", {}).get("value"),
                "qid": qid,
                "wikidata_label": entity.get("labels", {}).get("en", {}).get("value"),
                "description": entity.get("descriptions", {})
                .get("en", {})
                .get("value"),
                "instance_of": types,
                "authority_id_confirmed": authority_match,
                "musicbrainz_artists": overlap.get(qid, 0),
                "flags": flags,
            }
        )
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT,
        "scope": (
            "Targeted follow-up of suspected Detmold Person links."
            if args.qids
            else "Convenience sample of asserted Detmold Person links; not a population accuracy estimate. Missing Q5 or authority IDs requires review, not automatic deletion."
        ),
        "count": len(rows),
        "flagged": sum(bool(row["flags"]) for row in rows),
        "authority_ids_confirmed": sum(
            row["authority_id_confirmed"] is True for row in rows
        ),
        "with_musicbrainz_overlap": sum(row["musicbrainz_artists"] > 0 for row in rows),
        "links": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "links"}, indent=2
        )
    )
    for row in rows:
        if row["flags"]:
            print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
