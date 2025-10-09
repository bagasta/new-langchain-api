import json
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
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
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console

    # Performance
    MAX_CONCURRENT_AGENTS: int = 10000
    AGENT_EXECUTION_TIMEOUT: int = 300  # 5 minutes

    MCP_SSE_URL: Optional[str] = Field(default=None, env="MCP_SSE_URL")
    MCP_SSE_TOKEN: Optional[str] = Field(default=None, env="MCP_SSE_TOKEN")
    MCP_SSE_ALLOWED_TOOLS: List[str] = Field(default_factory=list, env="MCP_SSE_ALLOWED_TOOLS")

    MCP_HTTP_URL: Optional[str] = Field(default=None, env="MCP_HTTP_URL")
    MCP_HTTP_TOKEN: Optional[str] = Field(default=None, env="MCP_HTTP_TOKEN")
    MCP_HTTP_ALLOWED_TOOLS: List[str] = Field(default_factory=list, env="MCP_HTTP_ALLOWED_TOOLS")

    @field_validator("MCP_SSE_ALLOWED_TOOLS", "MCP_HTTP_ALLOWED_TOOLS", mode="before")
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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
