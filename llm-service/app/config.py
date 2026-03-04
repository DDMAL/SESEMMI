from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str
    llm_model: str = "gemini-2.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    rag_enabled: bool = False
    rag_top_k: int = 5
    few_shot_enabled: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/sesemmi"


settings = Settings()
