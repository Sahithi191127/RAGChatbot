"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    chroma_path: str = "./data/index/chroma"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    use_llm_stub: bool = False
    rate_limit_per_minute: int = 30
    max_message_length: int = 4000
    schedule_hour_utc: int = 2
    use_cache: bool = False
    fetch_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
