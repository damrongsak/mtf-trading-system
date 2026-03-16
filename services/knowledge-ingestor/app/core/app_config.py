import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("OlympusConfig")

class AppConfig:
    """Central configuration management for Olympus Ingestor"""
    
    def __init__(self, env_file: str = ".env"):
        self.base_dir = Path(__file__).parent.absolute()
        self.load_env(env_file)
        
        # FalkorDB settings
        self.falkor_host = os.getenv("FALKOR_HOST", "localhost")
        self.falkor_port = int(os.getenv("FALKOR_PORT", 6380))
        self.graph_name = os.getenv("GRAPH_NAME", "OlympusKnowledgeGraph")
        
        # LLM settings
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "google/gemini-2.5-flash")
        self.fallback_model_name = os.getenv("FALLBACK_MODEL_NAME", "google/gemini-2.0-flash-001")
        
        # Path settings
        self.root_dir = Path(__file__).parent.parent.parent.absolute()
        self.source_dir = self.root_dir / "source_data"
        self.archive_dir = self.source_dir / "archive"
        self.error_dir = self.source_dir / "errors"
        
        # Ensure directories exist
        try:
            self.source_dir.mkdir(exist_ok=True)
            self.archive_dir.mkdir(exist_ok=True)
            self.error_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")

    def load_env(self, env_file: str):
        """Load .env file if it exists"""
        env_path = self.base_dir / env_file
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        # Remove quotes if present
                        val = val.strip("'\"")
                        os.environ.setdefault(key, val)
            logger.info(f"Loaded environment from {env_path}")
        else:
            logger.warning(f"No .env file found at {env_path}")

# Singleton instance
config = AppConfig()
