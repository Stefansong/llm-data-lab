from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration sourced from environment variables or .env files."""

    app_name: str = "LLM Data Lab"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    frontend_origin: str = Field(default="http://localhost:3000")

    database_url: str = Field(default="sqlite+aiosqlite:///./llm_data_lab.db")

    # LLM provider credentials
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    allowed_upload_extensions: List[str] = Field(default_factory=lambda: ["csv", "xlsx", "xls"])
    upload_dir: Path = Field(default=Path("./uploaded_datasets"))

    # LLM provider credentials (existing + new)
    openai_default_models: List[str] = Field(
        default_factory=lambda: ["gpt-4o", "gpt-4o-mini", "gpt-4.1"]
    )

    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_default_models: List[str] = Field(
        default_factory=lambda: ["deepseek-chat", "deepseek-coder"]
    )

    dashscope_api_key: Optional[str] = None  # Qwen
    dashscope_base_url: str = Field(default="https://dashscope.aliyuncs.com")
    qwen_default_models: List[str] = Field(
        default_factory=lambda: ["qwen-turbo", "qwen-plus", "qwen-max"]
    )

    siliconflow_api_key: Optional[str] = None
    siliconflow_base_url: str = Field(default="https://api.siliconflow.cn")
    siliconflow_default_models: List[str] = Field(
        default_factory=lambda: ["siliconflow-chat", "siliconflow-coder"]
    )

    credentials_secret_key: Optional[str] = Field(
        default=None,
        description="Optional base64/UTF-8 secret for encrypting stored provider credentials. Falls back to JWT secret if omitted.",
    )

    jwt_secret_key: str = Field(
        default="change-me-change-me-change-me-change",
        min_length=32,
        description="Secret key used to sign JWT access tokens.",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expires_minutes: int = Field(default=43200)  # 30 days

    max_code_execution_seconds: int = Field(default=60)
    max_code_execution_memory_mb: int = Field(default=768)
    artifacts_dir: Path = Field(default=Path("./analysis_artifacts"))

    class Config:
        env_file = str(Path(__file__).resolve().parent / ".env")
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings
