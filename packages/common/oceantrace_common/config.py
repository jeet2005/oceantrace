from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OT_", env_file=".env", extra="ignore")

    app_name: str = "OCEANTRACE"
    environment: str = "local"
    database_url: str = "postgresql+psycopg2://oceantrace:oceantrace@localhost:5432/oceantrace"
    redis_url: str = "redis://localhost:6379/0"
    data_root: Path = Path("data")
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:3b"
    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_provider: str = "huggingface"
    reranker_model: str = "BAAI/bge-reranker-base"
    qdrant_url: str = "http://localhost:6333"
    default_particle_count: int = Field(default=250, ge=1)


settings = Settings()

