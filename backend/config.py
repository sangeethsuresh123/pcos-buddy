from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-3-27b-it"
    chroma_persist_dir: str = str(Path(__file__).parent / "chroma_db")
    knowledge_dir: str = str(Path(__file__).parent / "knowledge" / "pcos_docs")
    host: str = "0.0.0.0"
    port: int = 8000
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    max_memory_turns: int = 10
    temperature: float = 0.3
    max_tokens: int = 2048


settings = Settings()
