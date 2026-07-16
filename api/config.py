from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    database_url: str = "postgresql://copilot:copilot@postgres:5432/copilot"
    redis_url: str = "redis://redis:6379/0"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieve_top_k: int = 5
    retrieve_candidate_limit: int = 20
    rrf_k: int = 60


settings = Settings()
