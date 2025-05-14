import os
from typing import Dict, Any, Optional
from pathlib import Path
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration manager for DeepSearch system."""
    
    DEFAULT_CONFIG = {
        # Search settings
        "max_sources": 3,
        "max_iterations": 5,
        "web_search_provider": "serper",
        "reranker": "jina",
        "pro_mode": True,
        
        # API keys and credentials
        "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        "web_search_api_key": os.getenv("WEB_SEARCH_API_KEY", ""),
        "jina_api_key": os.getenv("JINA_API_KEY", ""),
        
        # Model settings
        "model_name": "gemini-2.0-flash-001",
        
        # Cache settings
        "cache_enabled": False,
        "cache_max_age_days": 7,
        
        # Advanced settings
        "retry_max_attempts": 3,
        "retry_initial_delay": 1.0,
        "retry_base": 2.0,
        "retry_jitter": True,
        
        # Logging
        "verbose": False,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration with default values and load custom config.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Determine config path
        if config_path is None:
            home_dir = Path.home()
            config_dir = os.path.join(home_dir, ".openprobe")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.json")
        
        self.config_path = config_path
        
        # Load configuration if exists
        self.load()
    
    def load(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
                    if self.config.get("verbose"):
                        print(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                if self.config.get("verbose"):
                    print(f"Saved configuration to {self.config_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            The configuration value or default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update multiple configuration values.
        
        Args:
            config_dict: Dictionary of configuration values
        """
        self.config.update(config_dict)
    
    def show(self) -> Dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            The current configuration dictionary
        """
        return self.config.copy()
    
    def reset(self) -> None:
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()


# Global config instance
config = Config()