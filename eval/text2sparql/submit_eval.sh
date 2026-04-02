#!/bin/bash
#SBATCH --job-name=sesemmi-t2s-eval
#SBATCH --account=def-ichiro_gpu
#SBATCH --time=02:00:00
#SBATCH --partition=gpubase_bygpu_b1
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --output=eval/runs/%x-%j.out
#SBATCH --error=eval/runs/%x-%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=yinan.a.zhou@gmail.com

# ── Configurable parameters (override via sbatch --export=ALL,...) ──
RUN_NAME="${RUN_NAME:-slurm-${SLURM_JOB_ID}}"
LLM_MODEL="${LLM_MODEL:-qwen3:4b}"
EVAL_TIMEOUT="${EVAL_TIMEOUT:-600}"
SERVICE_PORT="${SERVICE_PORT:-8000}"
ADAPTER_PORT="${ADAPTER_PORT:-8001}"
QUESTIONS_FILE="${QUESTIONS_FILE:-eval/text2sparql/questions.yml}"
GOLD_FILE="${GOLD_FILE:-eval/text2sparql/gold.yml}"

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
PROJECT_DIR="${SLURM_SUBMIT_DIR:-$(dirname "$(dirname "$SCRIPT_DIR")")}"
VENV_DIR="${PROJECT_DIR}/.venv-eval"
OUTPUT_DIR="${SCRATCH:-${PROJECT_DIR}}/sesemmi-evals"
RUN_DIR="$OUTPUT_DIR/$(date +%Y%m%d_%H%M%S)_${RUN_NAME}"
mkdir -p "$RUN_DIR"

# ── Cleanup on exit ──
cleanup() {
    echo "Cleaning up..."
    for pid in $ADAPTER_PID $UVICORN_PID $OLLAMA_PID $POSTGRES_PID; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null
    done
    sleep 2
    for pid in $ADAPTER_PID $UVICORN_PID $OLLAMA_PID $POSTGRES_PID; do
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
    done
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
    pip install -r "$PROJECT_DIR/llm-service/requirements.txt" 2>/dev/null \
        || pip install fastapi uvicorn httpx langchain langchain-ollama langgraph rdflib pydantic-settings langchain-core langchain-postgres langsmith
    pip install httpx  # for adapter and run_eval.py
    pip install text2sparql-client || pip install text2sparql-client --no-deps
else
    source "$VENV_DIR/bin/activate"
    # Ensure text2sparql-client is installed
    python -c "import text2sparql_client" 2>/dev/null || pip install text2sparql-client
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
    PGPORT="${PGPORT:-15432}"
    PGDATA="${SCRATCH:-${PROJECT_DIR}}/sesemmi-pgdata"
    mkdir -p "$PGDATA"

    if [ ! -f "$PGDATA/PG_VERSION" ]; then
        apptainer exec ~/postgres-pgvector.sif initdb -D "$PGDATA"
    fi

    apptainer exec ~/postgres-pgvector.sif \
        postgres -D "$PGDATA" -p "$PGPORT" -k "" &
    POSTGRES_PID=$!

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

    apptainer exec ~/postgres-pgvector.sif \
        psql -h localhost -p "$PGPORT" -d postgres \
        -c "CREATE DATABASE sesemmi;" 2>/dev/null || true

    export DATABASE_URL="postgresql+psycopg://$(whoami)@localhost:${PGPORT}/sesemmi"

    echo "Pulling embedding model: $EMBEDDING_MODEL"
    apptainer run --nv ~/ollama.sif pull "$EMBEDDING_MODEL"
fi

# ── Start llm-service ──
echo "=== Starting llm-service on port $SERVICE_PORT ==="
(cd "$PROJECT_DIR/llm-service" && uvicorn app.main:app --host 0.0.0.0 --port "$SERVICE_PORT") &
UVICORN_PID=$!

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

# ── Start TEXT2SPARQL adapter ──
echo "=== Starting TEXT2SPARQL adapter on port $ADAPTER_PORT ==="
python "$PROJECT_DIR/eval/text2sparql/adapter.py" \
    --port "$ADAPTER_PORT" \
    --service-url "http://localhost:${SERVICE_PORT}" \
    --virtuoso-endpoint "$VIRTUOSO_ENDPOINT" &
ADAPTER_PID=$!

for i in $(seq 1 15); do
    if curl -sf "http://localhost:${ADAPTER_PORT}/health" >/dev/null 2>&1; then
        echo "TEXT2SPARQL adapter is ready"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "ERROR: TEXT2SPARQL adapter failed to start after 15s" >&2
        exit 1
    fi
    sleep 1
done

# ── Run evaluation ──
echo "=== Running text2sparql evaluation ==="
echo "Run name:       $RUN_NAME"
echo "Model:          $LLM_MODEL"
echo "Questions:      $QUESTIONS_FILE"
echo "Output dir:     $RUN_DIR"
echo ""

# Step 1: Get predicted SPARQL via the TEXT2SPARQL adapter
echo "--- Step 1: Sending questions to TEXT2SPARQL adapter ---"
text2sparql ask "$PROJECT_DIR/$QUESTIONS_FILE" "http://localhost:${ADAPTER_PORT}" \
    --timeout "$EVAL_TIMEOUT" \
    --no-cache \
    -o "$RUN_DIR/predictions.json"

echo "Predictions saved to $RUN_DIR/predictions.json"

# Step 2: Execute predicted SPARQL against Virtuoso to get result sets
echo "--- Step 2: Executing predicted SPARQL against Virtuoso ---"
text2sparql query "$PROJECT_DIR/$QUESTIONS_FILE" \
    -a "$RUN_DIR/predictions.json" \
    -e "$VIRTUOSO_ENDPOINT" \
    -o "$RUN_DIR/pred_results.json"

echo "Predicted result sets saved to $RUN_DIR/pred_results.json"

# Step 3: If gold SPARQL exists, generate ground truth and evaluate
GOLD_PATH="$PROJECT_DIR/$GOLD_FILE"
if [ -f "$GOLD_PATH" ]; then
    # Check if gold.yml has actual SPARQL (not just TODOs)
    if grep -q "^    SELECT\|^    PREFIX\|^    ASK\|^    CONSTRUCT" "$GOLD_PATH" 2>/dev/null; then
        echo "--- Step 3: Building gold answers from $GOLD_FILE ---"
        python -c "
import yaml, json, sys
with open('$GOLD_PATH') as f:
    gold = yaml.safe_load(f)
with open('$PROJECT_DIR/$QUESTIONS_FILE') as f:
    qs = yaml.safe_load(f)
dataset_id = qs['dataset']['id']
prefix = qs.get('dataset', {}).get('prefix', dataset_id)
answers = []
for q in qs['questions']:
    qid = q['id']
    sparql = gold.get('queries', {}).get(qid, '')
    if sparql and not sparql.strip().startswith('# TODO'):
        for lang, text in q['question'].items():
            answers.append({
                'dataset': dataset_id,
                'question': text,
                'query': sparql.strip(),
                'endpoint': '$VIRTUOSO_ENDPOINT',
                'qname': f'{prefix}:{qid}-{lang}',
                'uri': f'{dataset_id}:{qid}'
            })
if not answers:
    print('No gold SPARQL found, skipping evaluation', file=sys.stderr)
    sys.exit(1)
with open('$RUN_DIR/gold_answers.json', 'w') as f:
    json.dump(answers, f, indent=2)
print(f'Gold answers: {len(answers)} queries')
" && {
            echo "--- Step 4: Executing gold SPARQL against Virtuoso ---"
            text2sparql query "$PROJECT_DIR/$QUESTIONS_FILE" \
                -a "$RUN_DIR/gold_answers.json" \
                -e "$VIRTUOSO_ENDPOINT" \
                -o "$RUN_DIR/true_results.json"

            echo "--- Step 5: Computing metrics ---"
            text2sparql evaluate "$RUN_NAME" \
                "$RUN_DIR/true_results.json" \
                "$RUN_DIR/pred_results.json" \
                -o "$RUN_DIR/metrics.json"

            echo ""
            echo "=== Metrics ==="
            cat "$RUN_DIR/metrics.json"
        }
    else
        echo "Gold SPARQL file has only TODOs, skipping ground truth evaluation"
    fi
else
    echo "No gold SPARQL file found at $GOLD_PATH, skipping ground truth evaluation"
fi

echo ""
echo "=== Job complete ==="
echo "Results: $RUN_DIR/"
ls -la "$RUN_DIR/"
