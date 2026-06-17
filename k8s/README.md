# SESEMMI — Kubernetes manifests

Plain YAML manifests to deploy SESEMMI into the **`sesemmi`** namespace. They replace the
Docker Compose stack with one in-cluster topology:

```
Ingress (nginx class, TLS) ──▶ Service app:80 ──▶ Deployment app (Next.js, :3000)
                                                        │ LLM_SERVICE_URL=http://llm:8000
                                                        ▼
                                              Service llm:8000 ──▶ Deployment llm (FastAPI)
                                                        │ DATABASE_URL=…@postgres:5432
                                                        ▼
                                              Service postgres:5432 ──▶ Deployment postgres (pgvector, emptyDir)
```

**Not in-cluster (external, via config):**
- **Virtuoso** triplestore — `VIRTUOSO_ENDPOINT` (default `https://virtuoso.simssa.ca/sparql`).
- **LLM provider** — Qwen/DashScope (`LLM_PROVIDER=qwen`, `DASHSCOPE_API_KEY`).
- **Ollama** — excluded. Only used for RAG embeddings; see the RAG note below.

## Files

| File | Resource(s) |
|---|---|
| `configmap.yaml` | `ConfigMap` sesemmi-config (non-secret env) |
| `secret.yaml` | `Secret` sesemmi-secrets (**placeholders — fill before applying**) |
| `postgres.yaml` | `Deployment` + `Service` postgres (ephemeral `emptyDir`) |
| `ollama.yaml` | `Deployment` + `Service` ollama (CPU, ephemeral; auto-pulls the embedding model for RAG) |
| `llm.yaml` | `Deployment` + `Service` llm (waits for postgres) |
| `app.yaml` | `Deployment` + `Service` app (2 replicas) |
| `ingress.yaml` | `Ingress` sesemmi (nginx class, TLS stub) |

> The `sesemmi` namespace is created via `kubectl create namespace sesemmi` (step 1 below),
> not a manifest file.

> Service names `llm`, `postgres`, and `ollama` are fixed — they match the hostnames already baked
> into `LLM_SERVICE_URL`, `DATABASE_URL`, and `OLLAMA_BASE_URL`, so no app config changes are needed.

## Deploy

1. **Create the namespace + GHCR image pull secret** (images are private at `ghcr.io/ddmal/sesemmi-*`):
   ```sh
   kubectl create namespace sesemmi
   kubectl -n sesemmi create secret docker-registry ghcr-pull-secret \
     --docker-server=ghcr.io \
     --docker-username=<github-user> \
     --docker-password=<github-PAT-with-read:packages>
   ```

2. **Fill in `secret.yaml`** — replace every `CHANGE_ME` (`POSTGRES_PASSWORD`,
   `DATABASE_URL` password must match it, `DASHSCOPE_API_KEY`, `LLM_API_KEY`). Prefer
   sealed-secrets / external-secrets for real environments rather than committing values.

3. **Set your host + TLS** in `ingress.yaml` (replace `sesemmi.example.com`; enable the
   `cert-manager.io/cluster-issuer` annotation, or provide your own `sesemmi-tls` secret).

4. **Pin image tags** (recommended): replace `:latest` in `llm.yaml` / `app.yaml`.

5. **Apply:**
   ```sh
   kubectl apply -f k8s/
   kubectl -n sesemmi rollout status deploy/postgres deploy/llm deploy/app
   ```

## RAG / embeddings note

`RAG_ENABLED=true`. On every llm startup the lifespan re-seeds pgvector — which is *why Postgres
uses ephemeral `emptyDir`* (no persistence needed). The seeder embeds via **Ollama**
(`app/rag/embeddings.py`, `OllamaEmbeddings` at `OLLAMA_BASE_URL`), regardless of `LLM_PROVIDER`.

Ollama runs **in-cluster** (`ollama.yaml`) at `http://ollama:11434`, CPU-only, with ephemeral
storage. Its Deployment auto-pulls `EMBEDDING_MODEL` (`nomic-embed-text`) via a `postStart` hook
and only becomes **Ready** once the model is present — so the model is re-pulled (~275MB) on every
Ollama pod restart.

Startup ordering: `llm` does not wait for Ollama, so if it starts first its RAG seeding fails and
the pod restarts until Ollama is Ready — k8s self-heals. To disable RAG entirely instead, set
`RAG_ENABLED=false` (then Ollama is unused).

## Verify

```sh
# Manifests lint without a cluster:
kubectl apply --dry-run=client -f k8s/

# In-cluster health:
kubectl -n sesemmi get pods
kubectl -n sesemmi exec deploy/app -- wget -qO- http://llm:8000/health   # {"status":"ok"}
kubectl -n sesemmi port-forward svc/app 8080:80                          # then curl :8080/api/health
kubectl -n sesemmi logs deploy/llm                                       # confirm RAG seed completed
```
