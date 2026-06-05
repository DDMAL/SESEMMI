from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is three levels up from this file (llm-service/app/config.py)
_ROOT_ENV = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV), env_file_encoding="utf-8", extra="ignore"
    )

    # LLM provider — ollama | openai | anthropic | gemini | qwen
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:1.7b"

    # API keys — fill all; only the active provider's key is used
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    dashscope_api_key: str | None = None
    qwen_base_url: str = "https://ws-1vm56exj78uoz68h.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"

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
    wikidata_mcp_url: str = "https://wd-mcp.wmcloud.org/mcp/"
    max_repair_iterations: int = 3
    semantic_judge_enabled: bool = True
    langsmith_api_key: str | None = None
    langsmith_project: str = "sesemmi-agent"
    langsmith_tracing: bool = False
    sparql_timeout: int = 120  # seconds; increase for slow federated queries


settings = Settings()
