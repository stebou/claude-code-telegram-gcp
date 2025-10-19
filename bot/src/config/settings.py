"""
Configuration settings for the Telegram bot.
Loads environment variables and validates configuration.
"""
import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration settings loaded from environment variables."""

    # Telegram Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(..., env="TELEGRAM_BOT_USERNAME")

    # Security
    approved_directory: Path = Field(..., env="APPROVED_DIRECTORY")
    allowed_users: List[int] = Field(..., env="ALLOWED_USERS")

    # Claude Configuration
    use_sdk: bool = Field(False, env="USE_SDK")
    claude_max_turns: int = Field(10, env="CLAUDE_MAX_TURNS")
    claude_max_cost_per_user: float = Field(10.0, env="CLAUDE_MAX_COST_PER_USER")
    claude_timeout_seconds: int = Field(900, env="CLAUDE_TIMEOUT_SECONDS")
    claude_allowed_tools: List[str] = Field(
        default=[
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Glob",
            "Grep",
            "Task",
            "WebFetch",
            "WebSearch",
            "TodoWrite",
            "Skill",
            "SlashCommand",
            "AskUserQuestion",
        ],
        env="CLAUDE_ALLOWED_TOOLS",
    )

    # Rate Limiting
    rate_limit_requests: int = Field(10, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")

    # Features
    enable_file_uploads: bool = Field(True, env="ENABLE_FILE_UPLOADS")

    # Development
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Database
    database_url: str = Field("sqlite:///telegram_bot.db", env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
