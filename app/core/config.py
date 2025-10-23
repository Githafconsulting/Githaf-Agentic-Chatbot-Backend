"""
Configuration settings for the application
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Githaf Chatbot API"

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Groq API
    GROQ_API_KEY: str

    # Embedding Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS - Allow all origins for widget embedding on third-party sites
    # Use ["*"] to allow all origins, or specify individual domains for production
    ALLOWED_ORIGINS: List[str] = ["*"]  # Allows widget to work on any domain

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # RAG Configuration
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.4  # Lowered to 0.4 for better recall (was 0.5, originally 0.7)
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # LLM Configuration
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 500

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


# Global settings instance
settings = Settings()
