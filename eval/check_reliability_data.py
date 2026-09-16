#!/usr/bin/env python3
"""Run the saved, read-only data probes behind the five UI examples. No LLM calls.

These probes check available data, not generated-query quality or full answers.
Requests run sequentially, without retries, with a 10-second client timeout.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((ROOT / "reliability_cases.json").read_text())
    results = []
    for case in cases:
        started = time.monotonic()
        row = {
            "id": case["id"],
            "question": case["question"],
            "probe": case["data_probe"],
        }
        try:
            url = "https://virtuoso.simssa.ca/sparql?" + urlencode(
                {
                    "query": case["data_probe"],
                    "format": "application/sparql-results+json",
                    "timeout": 10000,
                }
            )
            request = Request(url, headers={"User-Agent": "SESEMMI-data-check/1.0"})
            with urlopen(request, timeout=10) as response:
                row["result"] = json.load(response)
            row["error"] = None
        except Exception as exc:
            row["error"] = str(exc)
        row["duration_ms"] = round((time.monotonic() - started) * 1000)
        results.append(row)
        print(case["id"], row.get("result", row["error"]), flush=True)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Data availability probes only. No model evaluation or complete-answer verification.",
        "checks": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
