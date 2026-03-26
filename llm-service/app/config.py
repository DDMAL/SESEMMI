from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_model: str = "qwen3:1.7b"
    ollama_base_url: str = "http://ollama:11434"
    ollama_num_ctx: int = 8192  # context length
    ollama_num_thread: int = 2
    ollama_think: bool = False  # Qwen3 thinking mode — keep False on CPU (slow)

    # Embeddings (used only when RAG_ENABLED=true)
    embedding_model: str = "nomic-embed-text"
    rag_enabled: bool = False
    rag_top_k: int = 5
    few_shot_enabled: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/sesemmi"
    virtuoso_endpoint: str = "http://virtuoso:8890/sparql"
    max_repair_iterations: int = 3
    graph_enabled: bool = True
    semantic_judge_enabled: bool = True
    langsmith_api_key: str | None = None
    langsmith_project: str = "sesemmi-agent"
    langsmith_tracing: bool = False
    sparql_timeout: int = 120  # seconds; increase for slow federated queries


settings = Settings()
