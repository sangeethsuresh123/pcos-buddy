from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-3-27b-it"
    chroma_persist_dir: str = str(Path(__file__).parent / "chroma_db")
    weight_db_path: str = str(Path(__file__).parent / "data" / "weight.db")
    knowledge_dir: str = str(Path(__file__).parent / "knowledge" / "pcos_docs")
    host: str = "0.0.0.0"
    port: int = 8000
    auth_db_path: str = str(Path(__file__).parent / "data" / "auth.db")
    auth_cookie_name: str = "pcos_session"
    session_ttl_days: int = 30
    auth_pbkdf2_iterations: int = 600_000
    cookie_secure: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    max_memory_turns: int = 10
    temperature: float = 0.3
    max_tokens: int = 2048


settings = Settings()
