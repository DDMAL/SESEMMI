#!/usr/bin/env python3
"""SESEMMI evaluation script.

Sends natural-language queries to the llm-service /translate endpoint
and records structured results for experiment tracking.

Usage:
    # Single query
    python eval/run_eval.py --query "Find all compositions in DIAMM by Guillaume de Machaut"

    # Batch from JSON file
    python eval/run_eval.py --data eval/queries.json

    # Full options
    python eval/run_eval.py --data eval/queries.json \
        --service-url http://localhost:8000 \
        --output-dir eval/runs \
        --run-name "qwen3-1.7b-baseline" \
        --timeout 300
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


def get_git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def load_queries(args: argparse.Namespace) -> list[dict]:
    """Return a list of {id, query} dicts from CLI args."""
    if args.query:
        return [{"id": "cli-1", "query": args.query}]
    with open(args.data) as f:
        entries = json.load(f)
    for entry in entries:
        if "id" not in entry or "query" not in entry:
            print(f"ERROR: each entry in {args.data} must have 'id' and 'query' fields", file=sys.stderr)
            sys.exit(1)
    return entries


def create_run_dir(output_dir: str, run_name: str | None) -> Path:
    """Create and return a timestamped run directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{timestamp}_{run_name}" if run_name else timestamp
    run_dir = Path(output_dir) / name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_config(run_dir: Path, args: argparse.Namespace) -> None:
    """Snapshot the eval configuration for reproducibility."""
    config = {
        "service_url": args.service_url,
        "timeout": args.timeout,
        "data": args.data,
        "query": args.query,
        "run_name": args.run_name,
        "git_sha": get_git_sha(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")


def run_single_query(
    client: httpx.Client, service_url: str, query_id: str, query: str, timeout: float
) -> dict:
    """Send one query to /translate and return a result record."""
    record = {
        "id": query_id,
        "query": query,
        "sparql": None,
        "confidence": None,
        "assumptions": None,
        "graphs": None,
        "resultCount": None,
        "executionError": None,
        "durationMs": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }
    try:
        t0 = time.monotonic()
        resp = client.post(
            f"{service_url}/translate",
            json={"query": query},
            timeout=timeout,
        )
        wall_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            record["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
            record["durationMs"] = wall_ms
            return record

        data = resp.json()
        record.update(
            {
                "sparql": data.get("sparql"),
                "confidence": data.get("confidence"),
                "assumptions": data.get("assumptions"),
                "graphs": data.get("graphs"),
                "resultCount": data.get("resultCount"),
                "executionError": data.get("executionError"),
                "durationMs": data.get("durationMs", wall_ms),
            }
        )
    except httpx.TimeoutException:
        record["error"] = f"Timeout after {timeout}s"
        record["durationMs"] = int(timeout * 1000)
    except Exception as e:
        record["error"] = str(e)

    return record


def compute_summary(results: list[dict]) -> dict:
    """Compute basic aggregate stats from result records."""
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    durations = [r["durationMs"] for r in results if r["durationMs"] is not None]

    confidences = {}
    for r in results:
        c = r.get("confidence") or "none"
        confidences[c] = confidences.get(c, 0) + 1

    return {
        "total": total,
        "errors": errors,
        "success": total - errors,
        "avgDurationMs": int(sum(durations) / len(durations)) if durations else None,
        "minDurationMs": min(durations) if durations else None,
        "maxDurationMs": max(durations) if durations else None,
        "confidenceDistribution": confidences,
    }


def main():
    parser = argparse.ArgumentParser(description="SESEMMI evaluation runner")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--query", help="Single natural-language query")
    input_group.add_argument("--data", help="Path to queries JSON file")
    parser.add_argument(
        "--service-url",
        default="http://localhost:8000",
        help="llm-service base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output-dir",
        default="eval/runs",
        help="Base directory for run outputs (default: eval/runs)",
    )
    parser.add_argument("--run-name", help="Name for this run (default: timestamp only)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Per-query timeout in seconds (default: 300)",
    )
    args = parser.parse_args()

    queries = load_queries(args)
    run_dir = create_run_dir(args.output_dir, args.run_name)
    save_config(run_dir, args)

    print(f"Run directory: {run_dir}")
    print(f"Service URL:   {args.service_url}")
    print(f"Queries:       {len(queries)}")
    print()

    results = []
    results_path = run_dir / "results.jsonl"

    with httpx.Client() as client:
        for i, entry in enumerate(queries, 1):
            qid = entry["id"]
            query = entry["query"]
            print(f"[{i}/{len(queries)}] {qid}: {query[:80]}...", flush=True)

            record = run_single_query(client, args.service_url, qid, query, args.timeout)
            results.append(record)

            # Append to JSONL incrementally (survives crashes)
            with open(results_path, "a") as f:
                f.write(json.dumps(record) + "\n")

            status = record["confidence"] or "ERROR"
            if record["error"]:
                status = f"ERROR: {record['error'][:60]}"
            print(f"         -> {status} ({record['durationMs']}ms)")

    summary = compute_summary(results)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print()
    print(f"Done. {summary['success']}/{summary['total']} succeeded.")
    print(f"Results: {results_path}")
    print(f"Summary: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
