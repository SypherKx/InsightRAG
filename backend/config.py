"""
Backend configuration.

Environment-based configuration using pydantic-settings.
"""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)

is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "InsightRAG AI"
    app_version: str = "1.0.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    # Database
    database_url: str = "sqlite:////tmp/insightforge.db" if is_serverless else "sqlite:///./insightforge.db"

    # File storage
    upload_dir: str = "/tmp/uploads" if is_serverless else "./uploads"
    max_upload_size_mb: int = 500

    # LLM
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # RAG
    rag_index_path: str = "/tmp/rag_index" if is_serverless else "./rag_index"
    rag_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    def ensure_dirs(self):
        """Create necessary directories safely."""
        try:
            Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create upload_dir {self.upload_dir}: {e}")

        try:
            Path(self.rag_index_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create rag_index_path {self.rag_index_path}: {e}")


settings = Settings()
