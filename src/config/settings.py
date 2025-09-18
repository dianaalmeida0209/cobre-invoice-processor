# src/config/settings.py
"""
Application settings and configuration management
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    """Application configuration settings"""
    
    # API Configuration
    anthropic_api_key: str
    model_name: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 600
    temperature: float = 0.1
    
    # Processing Configuration
    enable_caching: bool = True
    rate_limit_delay: float = 0.1
    max_content_length: int = 1200
    
    # Performance Settings
    default_batch_size: int = 10
    max_workers: int = 10
    cache_ttl_seconds: int = 3600
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables"""
        # Load from .env file if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not installed, use os.getenv only
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        return cls(
            anthropic_api_key=api_key,
            model_name=os.getenv("MODEL_NAME", "claude-3-5-sonnet-20241022"),
            max_tokens=int(os.getenv("MAX_TOKENS", "600")),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            rate_limit_delay=float(os.getenv("RATE_LIMIT_DELAY", "0.1")),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "1200")),
            default_batch_size=int(os.getenv("DEFAULT_BATCH_SIZE", "10")),
            max_workers=int(os.getenv("MAX_WORKERS", "10")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    
    def validate(self) -> None:
        """Validate configuration settings"""
        if not self.anthropic_api_key or not self.anthropic_api_key.startswith("sk-ant-"):
            raise ValueError("Invalid Anthropic API key format")
        
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        
        if self.rate_limit_delay < 0:
            raise ValueError("rate_limit_delay cannot be negative")

# Global settings instance
settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global settings
    if settings is None:
        settings = Settings.from_env()
        settings.validate()
    return settings