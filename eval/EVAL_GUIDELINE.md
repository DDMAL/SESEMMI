# SESEMMI Evaluation Guide

This guide explains how to run evaluation experiments in the `eval/` directory.

---

## Overview

There are two evaluation pipelines:

| Pipeline | Script | Purpose |
|---|---|---|
| **Text2SPARQL benchmark** | `eval/text2sparql/local_eval.sh` | Full NL→SPARQL benchmark with accuracy metrics, using any LLM provider |
| **Text2SPARQL on DRAC** | `eval/text2sparql/submit_eval.sh` | Same benchmark submitted as a SLURM job on the DRAC cluster using Ollama |
| **Single-query eval** | `eval/submit_job.sh` | SLURM job for exploratory / single-question runs (no accuracy metrics) |

---

## Environment setup

Run these once before any eval script:

```bash
# Install Python dependencies for the llm-service (required by local_eval.sh and csv_to_yaml.py)
cd llm-service && uv sync && cd ..

# Install the text2sparql benchmark client as a standalone uv tool
uv tool install text2sparql-client
```

> `csv_to_yaml.py` depends on `pyyaml`, which is a transitive dependency of the llm-service.
> If you need to run it outside of that environment, install it directly: `uv tool install pyyaml` or `pip install pyyaml`.

---

## Step 0: Prepare the benchmark files

Before running an evaluation, convert your benchmark CSV into the YAML format expected by the `text2sparql-client` tool. The CSV can live anywhere and be named anything.

**Required CSV columns:** `id`, `category`, `nl` (natural-language question), `gold_sparql`

```bash
# Point --input at your CSV file
python3 eval/text2sparql/csv_to_yaml.py --input path/to/your_benchmark.csv

# Also specify where to write the output YAML files
python3 eval/text2sparql/csv_to_yaml.py \
  --input path/to/your_benchmark.csv \
  --output-dir eval/text2sparql/benchmark_yaml
```

This writes one pair of files per unique `category` value in the CSV:

```
<output-dir>/questions_<category>.yml
<output-dir>/gold_<category>.yml
```

If `--output-dir` is omitted, files are written next to the script at `eval/text2sparql/`.

---

## Step 1a: Local benchmark — external LLM providers

`eval/text2sparql/local_eval.sh` runs the full text2sparql evaluation pipeline locally. It starts the llm-service and a TEXT2SPARQL adapter, sends questions through the pipeline, executes the predicted SPARQL against Virtuoso, and computes accuracy metrics against gold SPARQL.

### Prerequisites

- Run from the project root directory
- API key exported in your shell (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`)
- Environment setup complete (see above)

### Run

```bash
# Default: OpenAI gpt-4o-mini
./eval/text2sparql/local_eval.sh

# Anthropic Claude
LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 \
  ./eval/text2sparql/local_eval.sh

# OpenAI
LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini \
  ./eval/text2sparql/local_eval.sh

# Google Gemini
LLM_PROVIDER=gemini LLM_MODEL=gemini-2.5-flash-lite \
  ./eval/text2sparql/local_eval.sh

# Local Ollama
LLM_PROVIDER=ollama LLM_MODEL=qwen3:4b \
  ./eval/text2sparql/local_eval.sh
```

### Run a specific category

Point `QUESTIONS_FILE` and `GOLD_FILE` at the files generated in Step 0:

```bash
QUESTIONS_FILE=eval/text2sparql/questions_cross_database.yml \
GOLD_FILE=eval/text2sparql/gold_cross_database.yml \
LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 \
  ./eval/text2sparql/local_eval.sh
```

### Outputs

Results are saved to a timestamped directory under `eval/runs/`:

```
eval/runs/<timestamp>_<run-name>/
  predictions.json     # predicted SPARQL for each question
  pred_results.json    # Virtuoso result sets for predictions
  gold_answers.json    # gold SPARQL formatted for the client
  true_results.json    # Virtuoso result sets for gold SPARQL
  metrics.json         # accuracy metrics (precision, recall, F1, etc.)
```

---

## Step 1b: DRAC cluster benchmark — Ollama models

`eval/text2sparql/submit_eval.sh` is a SLURM batch script for running the same benchmark on the DRAC (Digital Research Alliance of Canada) cluster using a locally-served Ollama model.

### Prerequisites

- SSH into your DRAC login node
- `~/ollama.sif` — Ollama Apptainer image available in your home directory
- `~/postgres-pgvector.sif` — PostgreSQL+pgvector Apptainer image (only needed when `RAG_ENABLED=true`)
- `LANGSMITH_API_KEY` exported in `~/.bashrc` (forwarded automatically via `sbatch --export=ALL`)

### Submit

```bash
# Default: qwen3:4b
sbatch --export=ALL eval/text2sparql/submit_eval.sh

# Custom model and run name
sbatch --export=ALL,LLM_MODEL=qwen3:14b,RUN_NAME=qwen3-14b-rag \
  eval/text2sparql/submit_eval.sh

# Specific benchmark category
sbatch --export=ALL,LLM_MODEL=qwen3:4b,\
QUESTIONS_FILE=eval/text2sparql/questions_cross_database.yml,\
GOLD_FILE=eval/text2sparql/gold_cross_database.yml \
  eval/text2sparql/submit_eval.sh

# Disable RAG (faster startup, no PostgreSQL required)
sbatch --export=ALL,RAG_ENABLED=false \
  eval/text2sparql/submit_eval.sh
```

### Key environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `qwen3:4b` | Ollama model to pull and use |
| `RUN_NAME` | `slurm-<job-id>` | Label for the output directory |
| `QUESTIONS_FILE` | `eval/text2sparql/questions.yml` | Questions YAML path (relative to project root) |
| `GOLD_FILE` | `eval/text2sparql/gold.yml` | Gold SPARQL YAML path |
| `RAG_ENABLED` | `true` | Enable pgvector RAG retrieval |
| `SEMANTIC_JUDGE_ENABLED` | `true` | Enable semantic judge re-ranking |
| `EVAL_TIMEOUT` | `600` | Per-question timeout in seconds |
| `VIRTUOSO_ENDPOINT` | `https://virtuoso.simssa.ca/sparql` | SPARQL endpoint for execution |

### Outputs

Results land in `$SCRATCH/sesemmi-evals/<timestamp>_<run-name>/` with the same structure as the local run (see above). SLURM stdout/stderr go to `eval/runs/<job-name>-<job-id>.{out,err}`.

---

## Step 1c: Single-question exploratory runs (DRAC)

`eval/submit_job.sh` is a lighter SLURM script for probing the pipeline with individual queries. It does **not** compute accuracy metrics — it just records the pipeline's SPARQL output and confidence score.

### Submit

```bash
# Single natural-language query
sbatch --export=ALL,EVAL_QUERY="Find all masses composed before 1400" \
  eval/submit_job.sh

# Batch from a JSON file
sbatch --export=ALL,EVAL_DATA=eval/queries.json \
  eval/submit_job.sh

# Custom model and run name
sbatch --export=ALL,\
LLM_MODEL=qwen3:1.7b,\
RUN_NAME=machaut-baseline,\
EVAL_QUERY="Find compositions by Guillaume de Machaut in DIAMM" \
  eval/submit_job.sh
```

### Input format for `eval/queries.json`

```json
[
  { "id": "q1", "query": "Find all masses composed before 1400" },
  { "id": "q2", "query": "List sources from the 15th century in RISM" }
]
```

### Outputs

Results are saved to `$SCRATCH/sesemmi-evals/<timestamp>_<run-name>/`:

```
results.jsonl    # one JSON record per query (SPARQL, confidence, duration, errors)
summary.json     # aggregate stats: success rate, avg/min/max duration, confidence distribution
config.json      # snapshot of eval parameters and git SHA for reproducibility
```

---

## Quick reference

```bash
# 1. Convert benchmark CSV → YAML
python3 eval/text2sparql/csv_to_yaml.py

# 2a. Run benchmark locally (external provider)
LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 \
  ./eval/text2sparql/local_eval.sh

# 2b. Submit benchmark to DRAC cluster
sbatch --export=ALL,LLM_MODEL=qwen3:4b eval/text2sparql/submit_eval.sh

# 2c. Submit a single exploratory query to DRAC
sbatch --export=ALL,EVAL_QUERY="Find masses in Cantus DB before 1300" \
  eval/submit_job.sh
```
