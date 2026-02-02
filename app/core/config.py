import json
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LangChain Agent API"

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # ~30 days

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")

    # Google OAuth
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(..., env="GOOGLE_REDIRECT_URI")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://localhost:5173", 
        "https://unprized-loriann-ceaselessly.ngrok-free.dev/", 
        "https://frontend-app.ngrok-free.app",
        "https://lfzlwlbz-5173.asse.devtunnels.ms",
        "https://b75650b1396e.ngrok-free.app",  # Current frontend
    ]

    # Database pool tuning
    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console

    # Performance
    MAX_CONCURRENT_AGENTS: int = 10000
    AGENT_EXECUTION_TIMEOUT: int = 300  # 5 minutes

    # Thread Pool for blocking operations (bcrypt, DB, etc.)
    # Thread Pool for blocking operations (bcrypt, DB, etc.)
    THREAD_POOL_SIZE: int = 100  # Large pool for high-concurrency load tests
    
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")

    MCP_SSE_URL: Optional[str] = Field(default=None, env="MCP_SSE_URL")
    MCP_SSE_TOKEN: Optional[str] = Field(default=None, env="MCP_SSE_TOKEN")
    MCP_SSE_ALLOWED_TOOLS: List[str] = Field(default_factory=list, env="MCP_SSE_ALLOWED_TOOLS")
    MCP_SSE_ALLOWED_TOOL_CATEGORIES: List[str] = Field(
        default_factory=list,
        env="MCP_SSE_ALLOWED_TOOL_CATEGORIES",
    )

    MCP_HTTP_URL: Optional[str] = Field(default=None, env="MCP_HTTP_URL")
    MCP_HTTP_TOKEN: Optional[str] = Field(default=None, env="MCP_HTTP_TOKEN")
    MCP_HTTP_ALLOWED_TOOLS: List[str] = Field(default_factory=list, env="MCP_HTTP_ALLOWED_TOOLS")

    @field_validator(
        "MCP_SSE_ALLOWED_TOOLS",
        "MCP_HTTP_ALLOWED_TOOLS",
        "MCP_SSE_ALLOWED_TOOL_CATEGORIES",
        mode="before",
    )
    @classmethod
    def _split_allowed_tools(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

settings = Settings()

# Shared ThreadPoolExecutor for blocking operations
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=settings.THREAD_POOL_SIZE)
