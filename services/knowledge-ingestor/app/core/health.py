"""
StartupGuard — Institutional Health Checker
============================================
Validates connectivity to all 3 LLM tiers independently:
  Tier 1: OpenRouter / stepfun/step-3.5-flash:free
  Tier 2: OpenRouter / deepseek/deepseek-v3.2
  Tier 3: Google Gemini Direct SDK

Also validates FalkorDB/Redis and filesystem directories.
"""

import os
import requests
from redis import Redis
from typing import Dict
from app.core.app_config import config
from app.core.logger import get_logger

logger = get_logger("StartupGuard")

# ─────────────────────────── Per-Tier Health Checks ──────────────────────────

def _check_openrouter_model(model: str, tier_label: str) -> Dict:
    """
    Probe a specific OpenRouter model via the /generation endpoint.
    Returns a health dict: {status, model, provider, note}
    """
    if not config.openrouter_api_key:
        return {
            "tier": tier_label,
            "model": model,
            "provider": "openrouter",
            "status": "unconfigured",
            "note": "OPENROUTER_API_KEY not set",
        }
    try:
        # Use the models list endpoint — cheap, doesn't consume credits
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {config.openrouter_api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            # Verify the specific model is listed
            model_ids = [m.get("id", "") for m in resp.json().get("data", [])]
            found = model in model_ids
            return {
                "tier": tier_label,
                "model": model,
                "provider": "openrouter",
                "status": "healthy" if found else "model_not_found",
                "note": "OK" if found else f"Model '{model}' not listed in OpenRouter catalogue",
            }
        elif resp.status_code == 402:
            return {
                "tier": tier_label,
                "model": model,
                "provider": "openrouter",
                "status": "credit_exhausted",
                "note": "402 Payment Required — no credits remaining",
            }
        else:
            return {
                "tier": tier_label,
                "model": model,
                "provider": "openrouter",
                "status": "error",
                "note": f"HTTP {resp.status_code}",
            }
    except Exception as e:
        return {
            "tier": tier_label,
            "model": model,
            "provider": "openrouter",
            "status": "unreachable",
            "note": str(e),
        }


def _check_gemini_direct(model_id: str, tier_label: str) -> Dict:
    """
    Probe Google Generative Language API for a specific model.
    Returns a health dict: {status, model, provider, note}
    """
    if not config.google_api_key:
        return {
            "tier": tier_label,
            "model": model_id,
            "provider": "gemini_direct",
            "status": "unconfigured",
            "note": "GOOGLE_API_KEY not set",
        }
    try:
        # Strip provider prefix if present (e.g. "google/gemini-2.5-flash" → "gemini-2.5-flash")
        clean_model = model_id.split("/")[-1]
        url = (
            f"https://generativelanguage.googleapis.com/v1/models/{clean_model}"
            f"?key={config.google_api_key}"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return {
                "tier": tier_label,
                "model": model_id,
                "provider": "gemini_direct",
                "status": "healthy",
                "note": "OK",
            }
        else:
            return {
                "tier": tier_label,
                "model": model_id,
                "provider": "gemini_direct",
                "status": "error",
                "note": f"HTTP {resp.status_code}: {resp.text[:120]}",
            }
    except Exception as e:
        return {
            "tier": tier_label,
            "model": model_id,
            "provider": "gemini_direct",
            "status": "unreachable",
            "note": str(e),
        }


# ─────────────────────────── StartupGuard ────────────────────────────────────

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
    def check_llm_tiers() -> Dict[str, Dict]:
        """
        Check all 3 LLM tiers individually.
        Returns a dict keyed by tier name with health details.
        """
        results = {
            "tier1": _check_openrouter_model(config.tier1_model, "tier1"),
            "tier2": _check_openrouter_model(config.tier2_model, "tier2"),
            "tier3": _check_gemini_direct(config.tier3_model, "tier3"),
        }

        for tier, info in results.items():
            status = info["status"]
            model = info["model"]
            if status == "healthy":
                logger.info(f"✅ LLM {tier.upper()} ({model}): OK")
            elif status == "credit_exhausted":
                logger.warning(f"⚠️ LLM {tier.upper()} ({model}): Credit Exhausted — will skip to next tier")
            elif status == "unconfigured":
                logger.warning(f"⚠️ LLM {tier.upper()} ({model}): API key not configured")
            else:
                logger.error(f"❌ LLM {tier.upper()} ({model}): {status} — {info.get('note')}")

        # Alert if ALL tiers are degraded
        all_down = all(r["status"] not in ("healthy",) for r in results.values())
        if all_down:
            logger.critical(
                "🚨 ALL 3 LLM TIERS UNHEALTHY — ingestion will fail. "
                "Check OPENROUTER_API_KEY credits and GOOGLE_API_KEY validity."
            )

        return results

    @staticmethod
    def check_llm() -> bool:
        """Simple bool check — at least one tier must be healthy."""
        tiers = StartupGuard.check_llm_tiers()
        return any(t["status"] == "healthy" for t in tiers.values())

    @staticmethod
    def check_directories() -> bool:
        """Ensure required data directories exist and are writable."""
        dirs = [config.source_dir, config.archive_dir, config.error_dir]
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
        """Run all startup checks."""
        logger.info("🚀 Starting Olympus Ingestor Guardrails…")
        results = [
            cls.check_redis(),
            cls.check_llm(),
            cls.check_directories(),
        ]
        success = all(results)
        if success:
            logger.info("🏛️ Project Olympus Readiness: COMMAND AUTHORIZED")
        else:
            logger.critical("🚨 Project Olympus Readiness: MISSION ABORTED. Check infrastructure.")
        return success


if __name__ == "__main__":
    StartupGuard.run_all()
