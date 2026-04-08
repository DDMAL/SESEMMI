#!/bin/bash
#SBATCH --job-name=sesemmi-eval
#SBATCH --account=def-ichiro_gpu
#SBATCH --time=01:00:00
#SBATCH --partition=gpubase_bygpu_b1
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --output=eval/runs/%x-%j.out
#SBATCH --error=eval/runs/%x-%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=yinan.a.zhou@gmail.com

# ── Configurable parameters (override via sbatch --export=ALL,...) ──
EVAL_QUERY="${EVAL_QUERY:-}"            # single query mode (takes precedence over EVAL_DATA)
EVAL_DATA="${EVAL_DATA:-eval/queries.json}"
RUN_NAME="${RUN_NAME:-slurm-${SLURM_JOB_ID}}"
LLM_MODEL="${LLM_MODEL:-qwen3:1.7b}"
EVAL_TIMEOUT="${EVAL_TIMEOUT:-900}"
SERVICE_PORT="${SERVICE_PORT:-8000}"

# Pipeline config (env vars read by llm-service Settings)
export LLM_MODEL="${LLM_MODEL}"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-8192}"
export OLLAMA_NUM_THREAD="${OLLAMA_NUM_THREAD:-4}"
export OLLAMA_THINK="${OLLAMA_THINK:-false}"
export GRAPH_ENABLED="${GRAPH_ENABLED:-true}"
export SEMANTIC_JUDGE_ENABLED="${SEMANTIC_JUDGE_ENABLED:-true}"
export MAX_REPAIR_ITERATIONS="${MAX_REPAIR_ITERATIONS:-3}"
export VIRTUOSO_ENDPOINT="${VIRTUOSO_ENDPOINT:-https://virtuoso.simssa.ca/sparql}"
export RAG_ENABLED="${RAG_ENABLED:-true}"
export FEW_SHOT_ENABLED="${FEW_SHOT_ENABLED:-false}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"
export SPARQL_TIMEOUT="${SPARQL_TIMEOUT:-120}"

# LangSmith (set LANGSMITH_API_KEY in ~/.bashrc, forwarded via sbatch --export=ALL)
export LANGSMITH_TRACING="${LANGSMITH_TRACING:-true}"
export LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-sesemmi-eval}"

# ── Paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SLURM_SUBMIT_DIR:-$(dirname "$SCRIPT_DIR")}"
VENV_DIR="${PROJECT_DIR}/.venv-eval"
OUTPUT_DIR="${SCRATCH:-${PROJECT_DIR}}/sesemmi-evals"

# ── Cleanup on exit ──
cleanup() {
    echo "Cleaning up..."
    [ -n "$UVICORN_PID" ]   && kill "$UVICORN_PID"   2>/dev/null
    [ -n "$OLLAMA_PID" ]    && kill "$OLLAMA_PID"    2>/dev/null
    [ -n "$POSTGRES_PID" ]  && kill "$POSTGRES_PID"  2>/dev/null
    wait 2>/dev/null
}
trap cleanup EXIT

# ── Module and venv setup ──
echo "=== Setting up environment ==="
module load python/3.12 2>/dev/null || module load python 2>/dev/null
module load StdEnv/2023 apptainer/1.4.5

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR"
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$PROJECT_DIR/llm-service/requirements.txt" \
        || pip install fastapi uvicorn httpx langchain langchain-ollama langgraph rdflib pydantic-settings langchain-core langchain-postgres langsmith langchain-mcp-adapters mcp
    pip install httpx  # for run_eval.py
else
    source "$VENV_DIR/bin/activate"
fi

# ── Start Ollama ──
echo "=== Starting Ollama ==="
apptainer run --nv ~/ollama.sif serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Ollama failed to start after 30s" >&2
        exit 1
    fi
    sleep 1
done

# Pull model if not cached
echo "Pulling model: $LLM_MODEL"
apptainer run --nv ~/ollama.sif pull "$LLM_MODEL"

# ── Start PostgreSQL (only when RAG is enabled) ──
if [ "${RAG_ENABLED}" = "true" ]; then
    echo "=== Starting PostgreSQL ==="
    PGPORT="${PGPORT:-15432}"  # non-standard port to avoid system conflicts
    PGDATA="${SCRATCH:-${PROJECT_DIR}}/sesemmi-pgdata"
    mkdir -p "$PGDATA"

    # Initialize cluster if needed (idempotent)
    if [ ! -f "$PGDATA/PG_VERSION" ]; then
        apptainer exec ~/postgres-pgvector.sif initdb -D "$PGDATA"
    fi

    # Start postgres in background; -k "" disables Unix socket (read-only in Apptainer)
    apptainer exec ~/postgres-pgvector.sif \
        postgres -D "$PGDATA" -p "$PGPORT" -k "" &
    POSTGRES_PID=$!

    # Wait for it to be ready
    for i in $(seq 1 30); do
        if apptainer exec ~/postgres-pgvector.sif \
               pg_isready -h localhost -p "$PGPORT" >/dev/null 2>&1; then
            echo "PostgreSQL is ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "ERROR: PostgreSQL failed to start after 30s" >&2
            exit 1
        fi
        sleep 1
    done

    # Create database (idempotent)
    apptainer exec ~/postgres-pgvector.sif \
        psql -h localhost -p "$PGPORT" -d postgres \
        -c "CREATE DATABASE sesemmi;" 2>/dev/null || true

    export DATABASE_URL="postgresql+psycopg://$(whoami)@localhost:${PGPORT}/sesemmi"

    # Pull embedding model
    echo "Pulling embedding model: $EMBEDDING_MODEL"
    apptainer run --nv ~/ollama.sif pull "$EMBEDDING_MODEL"
fi

# ── Start llm-service ──
echo "=== Starting llm-service on port $SERVICE_PORT ==="
(cd "$PROJECT_DIR/llm-service" && uvicorn app.main:app --host 0.0.0.0 --port "$SERVICE_PORT") &
UVICORN_PID=$!

# Wait for llm-service health check
# When RAG_ENABLED=true, startup includes pgvector table creation (~30s) and
# first-time embedding model load into GPU memory (~25s), so allow 180s.
HEALTH_TIMEOUT=180
for i in $(seq 1 $HEALTH_TIMEOUT); do
    if curl -sf "http://localhost:${SERVICE_PORT}/health" >/dev/null 2>&1; then
        echo "llm-service is ready"
        break
    fi
    if [ "$i" -eq "$HEALTH_TIMEOUT" ]; then
        echo "ERROR: llm-service failed to start after ${HEALTH_TIMEOUT}s" >&2
        exit 1
    fi
    sleep 1
done

# ── Run evaluation ──
echo "=== Running evaluation ==="
echo "Run name:   $RUN_NAME"
echo "Model:      $LLM_MODEL"
echo "Output dir: $OUTPUT_DIR"

EVAL_ARGS=(
    --service-url "http://localhost:${SERVICE_PORT}"
    --output-dir "$OUTPUT_DIR"
    --run-name "$RUN_NAME"
    --timeout "$EVAL_TIMEOUT"
)

if [ -n "$EVAL_QUERY" ]; then
    echo "Query:      $EVAL_QUERY"
    EVAL_ARGS+=(--query "$EVAL_QUERY")
else
    echo "Data:       $EVAL_DATA"
    EVAL_ARGS+=(--data "$PROJECT_DIR/$EVAL_DATA")
fi
echo ""

python "$PROJECT_DIR/eval/run_eval.py" "${EVAL_ARGS[@]}"

echo "=== Job complete ==="
