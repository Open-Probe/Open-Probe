import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "OpenProbe API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Backend API for OpenProbe AI system"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_TIMEOUT: int = 60
    
    # Session Configuration
    MAX_CONCURRENT_SEARCHES: int = 10
    SEARCH_TIMEOUT: int = 300  # 5 minutes
    
    # DeepSearch Configuration
    MAX_REPLAN_ITER: int = 1
    RECURSION_LIMIT: int = 30
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
