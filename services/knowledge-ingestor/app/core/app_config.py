import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger("OlympusConfig")

class AppConfig:
    """Central configuration management for Olympus Ingestor"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent.absolute()
        # Load global .env from root if it exists, otherwise fallback to local
        global_env = self.root_dir.parent.parent / ".env"
        if global_env.exists():
            load_dotenv(global_env)
            logger.info(f"Loaded global environment from {global_env}")
        else:
            load_dotenv()
            logger.info("Loaded local environment")

        # FalkorDB settings
        self.falkor_host = os.getenv("FALKOR_HOST", "falkordb")
        self.falkor_port = int(os.getenv("FALKOR_PORT", 6379))
        self.graph_name = os.getenv("GRAPH_NAME", "OlympusKnowledgeGraph")
        
        # LLM settings
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "google/gemini-2.5-flash")
        self.fallback_model_name = os.getenv("FALLBACK_MODEL_NAME", "google/gemini-2.0-flash-001")
        
        # Path settings
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

# Singleton instance
config = AppConfig()
