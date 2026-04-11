#!/bin/bash
# local_eval.sh — run text2sparql evaluation locally with any LLM provider
#
# Usage:
#   LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 ./eval/text2sparql/local_eval.sh
#   LLM_PROVIDER=openai    LLM_MODEL=gpt-4o-mini               ./eval/text2sparql/local_eval.sh
#   LLM_PROVIDER=gemini    LLM_MODEL=gemini-2.5-flash-lite      ./eval/text2sparql/local_eval.sh
#   LLM_PROVIDER=ollama    LLM_MODEL=qwen3:4b                   ./eval/text2sparql/local_eval.sh
#
# Prerequisites:
#   - cd into project root before running
#   - API key exported in env (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY)
#   - llm-service venv active (or uv available): cd llm-service && uv sync
#   - text2sparql-client installed: uv tool install text2sparql-client

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Run config — edit here to change defaults ────────────────────────────────
# Priority: CLI env var > value set here > .env fallback (for API keys etc.)
RUN_NAME="${RUN_NAME:-local-anthropic-$(date +%Y%m%d_%H%M%S)}"
export LLM_PROVIDER="${LLM_PROVIDER:-anthropic}"
export LLM_MODEL="${LLM_MODEL:-claude-haiku-4-5}"
EVAL_TIMEOUT="${EVAL_TIMEOUT:-600}"
SERVICE_PORT="${SERVICE_PORT:-8000}"
ADAPTER_PORT="${ADAPTER_PORT:-8001}"
QUESTIONS_FILE="${QUESTIONS_FILE:-eval/text2sparql/questions.yml}"
GOLD_FILE="${GOLD_FILE:-eval/text2sparql/gold.yml}"
export VIRTUOSO_ENDPOINT="${VIRTUOSO_ENDPOINT:-https://virtuoso.simssa.ca/sparql}"
export GRAPH_ENABLED="${GRAPH_ENABLED:-true}"
export SEMANTIC_JUDGE_ENABLED="${SEMANTIC_JUDGE_ENABLED:-true}"
export RAG_ENABLED="${RAG_ENABLED:-false}"
export LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-sesemmi-eval}"

# ── Load .env for anything not set above (API keys, LangSmith key, etc.) ─────
# pydantic-settings reads the same .env automatically when uvicorn starts.
_env_load() {
    local file="$1"
    [ -f "$file" ] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
        local key="${line%%=*}"; key="${key//[[:space:]]/}"
        [[ -z "$key" || -n "${!key+x}" ]] && continue   # skip if already set
        local val; val="$(printf '%s' "${line#*=}" | sed 's/[[:space:]]*#.*$//')"
        export "$key=$val"
    done < "$file"
}
_env_load "$PROJECT_DIR/.env"
OUTPUT_DIR="${PROJECT_DIR}/eval/runs"
RUN_DIR="$OUTPUT_DIR/$(date +%Y%m%d_%H%M%S)_${RUN_NAME}"
mkdir -p "$RUN_DIR"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    echo "Cleaning up..."
    # Kill by PID and their children (uv spawns uvicorn as a child)
    [ -n "$ADAPTER_PID" ] && kill -- -"$ADAPTER_PID" 2>/dev/null; kill "$ADAPTER_PID" 2>/dev/null
    [ -n "$UVICORN_PID" ] && kill -- -"$UVICORN_PID" 2>/dev/null; kill "$UVICORN_PID" 2>/dev/null
    sleep 1
    # Force-kill anything still holding the ports
    lsof -ti :"$SERVICE_PORT" 2>/dev/null | xargs kill -9 2>/dev/null
    lsof -ti :"$ADAPTER_PORT" 2>/dev/null | xargs kill -9 2>/dev/null
    wait 2>/dev/null
}
trap cleanup EXIT

echo "=== text2sparql local eval ==="
echo "Provider:  $LLM_PROVIDER"
echo "Model:     $LLM_MODEL"
echo "Run name:  $RUN_NAME"
echo "Output:    $RUN_DIR"
echo ""

# ── Start llm-service ─────────────────────────────────────────────────────────
echo "=== Starting llm-service on port $SERVICE_PORT ==="
(cd "$PROJECT_DIR/llm-service" && uv run uvicorn app.main:app --host 0.0.0.0 --port "$SERVICE_PORT") &
UVICORN_PID=$!

for i in $(seq 1 60); do
    if curl -sf "http://localhost:${SERVICE_PORT}/health" >/dev/null 2>&1; then
        echo "llm-service is ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: llm-service failed to start after 60s" >&2
        exit 1
    fi
    sleep 1
done

# ── Start TEXT2SPARQL adapter ─────────────────────────────────────────────────
echo "=== Starting TEXT2SPARQL adapter on port $ADAPTER_PORT ==="
(cd "$PROJECT_DIR/llm-service" && uv run python "$PROJECT_DIR/eval/text2sparql/adapter.py" \
    --port "$ADAPTER_PORT" \
    --service-url "http://localhost:${SERVICE_PORT}" \
    --virtuoso-endpoint "$VIRTUOSO_ENDPOINT") &
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

# ── Helpers ───────────────────────────────────────────────────────────────────
# text2sparql-client conflicts with llm-service's uvicorn version, so it must
# be installed as a standalone uv tool: `uv tool install text2sparql-client`
t2s() { text2sparql "$@"; }
uvpy() { (cd "$PROJECT_DIR/llm-service" && uv run python "$@"); }

# ── Run evaluation ────────────────────────────────────────────────────────────
echo ""
echo "=== Running text2sparql evaluation ==="

# Step 1: Get predicted SPARQL via the TEXT2SPARQL adapter
echo "--- Step 1: Sending questions to TEXT2SPARQL adapter ---"
t2s ask "$PROJECT_DIR/$QUESTIONS_FILE" "http://localhost:${ADAPTER_PORT}" \
    --timeout "$EVAL_TIMEOUT" \
    --no-cache \
    -o "$RUN_DIR/predictions.json"
echo "Predictions saved to $RUN_DIR/predictions.json"

# Step 2: Execute predicted SPARQL against Virtuoso to get result sets
echo "--- Step 2: Executing predicted SPARQL against Virtuoso ---"
t2s query "$PROJECT_DIR/$QUESTIONS_FILE" \
    -a "$RUN_DIR/predictions.json" \
    -e "$VIRTUOSO_ENDPOINT" \
    -o "$RUN_DIR/pred_results.json"
echo "Predicted result sets saved to $RUN_DIR/pred_results.json"

# Step 3–5: Gold SPARQL evaluation (if available)
GOLD_PATH="$PROJECT_DIR/$GOLD_FILE"
if [ -f "$GOLD_PATH" ]; then
    if grep -q "^    SELECT\|^    PREFIX\|^    ASK\|^    CONSTRUCT" "$GOLD_PATH" 2>/dev/null; then
        echo "--- Step 3: Building gold answers from $GOLD_FILE ---"
        uvpy -c "
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
            t2s query "$PROJECT_DIR/$QUESTIONS_FILE" \
                -a "$RUN_DIR/gold_answers.json" \
                -e "$VIRTUOSO_ENDPOINT" \
                -o "$RUN_DIR/true_results.json"

            echo "--- Step 5: Computing metrics ---"
            t2s evaluate "$RUN_NAME" \
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
echo "=== Done ==="
echo "Results: $RUN_DIR/"
ls -la "$RUN_DIR/"
