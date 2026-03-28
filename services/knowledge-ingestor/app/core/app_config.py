import os
import logging
from pathlib import Path
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

        # ── FalkorDB ────────────────────────────────────────────
        self.falkor_host = os.getenv("FALKOR_HOST", "falkordb")
        self.falkor_port = int(os.getenv("FALKOR_PORT", 6379))
        self.graph_name = os.getenv("FALKOR_GRAPH_NAME", "OlympusKnowledgeGraph")

        # ── LLM API Keys ────────────────────────────────────────
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

        # ── 3-Tier Cascading LLM Strategy (from global .env) ────
        # Tier 1: OpenRouter primary model (free/low-cost)
        self.tier1_model = os.getenv("KI_TIER1_MODEL", "stepfun/step-3.5-flash:free")
        # Tier 2: OpenRouter secondary model (higher quality fallback)
        self.tier2_model = os.getenv("KI_TIER2_MODEL", "deepseek/deepseek-v3.2")
        # Tier 3: Direct Google Gemini (last resort, always available)
        self.tier3_model = os.getenv("KI_TIER3_MODEL", "google/gemini-2.5-flash")

        # Legacy aliases kept for backward compatibility
        self.model_name = self.tier1_model
        self.fallback_model_name = self.tier2_model

        # ── File System Paths ───────────────────────────────────
        self.source_dir = self.root_dir / "source_data"
        self.archive_dir = self.source_dir / "archive"
        self.error_dir = self.source_dir / "errors"

        try:
            self.source_dir.mkdir(exist_ok=True)
            self.archive_dir.mkdir(exist_ok=True)
            self.error_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")

    def __repr__(self) -> str:
        return (
            f"AppConfig(tier1={self.tier1_model}, tier2={self.tier2_model}, "
            f"tier3={self.tier3_model.split('/')[-1]}, "
            f"falkordb={self.falkor_host}:{self.falkor_port})"
        )


# Singleton instance
config = AppConfig()

