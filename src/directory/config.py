"""Configuration management."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find the project root directory (where .env should be)
# This is the parent of the parent of this file's directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Anthropic API configuration
    anthropic_api_key: str

    # Model configuration
    model: str = "claude-sonnet-4-20250514"

    # Output limits
    max_output_size: int = 100_000  # 100KB

    # Execution timeouts (seconds)
    read_timeout: int = 60
    write_timeout: int = 300


# Global settings instance
settings = Settings()
