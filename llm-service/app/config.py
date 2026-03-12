from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str
    llm_model: str = "gemini-2.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
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
