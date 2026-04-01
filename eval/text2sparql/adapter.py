#!/usr/bin/env python3
"""TEXT2SPARQL protocol adapter for SESEMMI.

Bridges the TEXT2SPARQL GET protocol to SESEMMI's POST /translate endpoint.

Usage:
    python eval/text2sparql/adapter.py --service-url http://localhost:8000
"""

import argparse

import httpx
import uvicorn
from fastapi import FastAPI, Query

app = FastAPI(title="SESEMMI TEXT2SPARQL Adapter")

SERVICE_URL = "http://localhost:8000"
VIRTUOSO_ENDPOINT = "https://virtuoso.simssa.ca/sparql"
TIMEOUT = 600.0


@app.get("/")
async def translate(
    question: str = Query(..., description="Natural language question"),
    dataset: str = Query(..., description="Target dataset identifier"),
):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{SERVICE_URL}/translate",
                json={"query": question},
            )
            sparql = resp.json().get("sparql", "") if resp.status_code == 200 else ""
        except Exception:
            sparql = ""

    return {
        "dataset": dataset,
        "question": question,
        "query": sparql,
        "endpoint": VIRTUOSO_ENDPOINT,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TEXT2SPARQL adapter for SESEMMI")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--service-url", default="http://localhost:8000")
    parser.add_argument(
        "--virtuoso-endpoint", default="https://virtuoso.simssa.ca/sparql"
    )
    args = parser.parse_args()

    SERVICE_URL = args.service_url
    VIRTUOSO_ENDPOINT = args.virtuoso_endpoint

    uvicorn.run(app, host="0.0.0.0", port=args.port)
