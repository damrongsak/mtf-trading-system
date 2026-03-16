import asyncio
import os
import requests
from redis import Redis
from app.core.app_config import config
from app.core.logger import get_logger

logger = get_logger("StartupGuard")

class StartupGuard:
    """Industrial-grade startup validation and health checks."""

    @staticmethod
    def check_redis() -> bool:
        """Verify Redis/FalkorDB connectivity."""
        try:
            r = Redis(host=config.falkor_host, port=config.falkor_port, socket_timeout=5)
            r.ping()
            logger.info("✅ Redis/FalkorDB Connectivity: OK")
            return True
        except Exception as e:
            logger.error(f"❌ Redis Connectivity Failed: {e}")
            return False

    @staticmethod
    def check_llm() -> bool:
        """Verify LLM Gateway (OpenRouter) reachability."""
        if not config.openrouter_api_key:
            logger.error("❌ OPENROUTER_API_KEY is missing!")
            return False
            
        try:
            # Quick check on models endpoint or basic auth check
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {config.openrouter_api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                logger.info("✅ LLM Gateway Connectivity: OK")
                return True
            else:
                logger.error(f"❌ LLM Gateway Returned Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ LLM Gateway Reachability Failed: {e}")
            return False

    @staticmethod
    def check_directories() -> bool:
        """Ensure required data directories exist and are writable."""
        dirs = [
            config.source_dir,
            config.archive_dir,
            config.error_dir
        ]
        for d in dirs:
            if not os.path.exists(d):
                try:
                    os.makedirs(d, exist_ok=True)
                    logger.info(f"📁 Created directory: {d}")
                except Exception as e:
                    logger.error(f"❌ Failed to create directory {d}: {e}")
                    return False
            if not os.access(d, os.W_OK):
                logger.error(f"❌ Directory not writable: {d}")
                return False
        logger.info("✅ Data Directories: OK")
        return True

    @classmethod
    def run_all(cls) -> bool:
        """Run all startup checks. Exits on failure in production."""
        logger.info("🚀 Starting Olympus Ingestor Guardrails...")
        
        results = [
            cls.check_redis(),
            cls.check_llm(),
            cls.check_directories()
        ]
        
        success = all(results)
        if success:
            logger.info("🏛️ Project Olympus Readiness: COMMAND AUTHORIZED")
        else:
            logger.critical("🚨 Project Olympus Readiness: MISSION ABORTED. Check infrastructure.")
            
        return success

if __name__ == "__main__":
    # Test run
    StartupGuard.run_all()
