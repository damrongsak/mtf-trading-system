import logging
import asyncio
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

class StabilityObserver:
    """
    Monitors the stability of external services and ML models.
    """
    
    def __init__(self):
        self.consecutive_failures = 0
        self.max_failures_threshold = 3
        self._is_running = False
        
    async def run_predictor_stability_check(self) -> Dict[str, Any]:
        """
        Main entry point for scheduled stability check of the Olympus Predictor.
        """
        if self._is_running:
            logger.warning("Stability check is already running. Skipping this execution.")
            return
            
        self._is_running = True
        
        logger.info("🛡️ Running Predictor Stability Check...")
        
        health_data = await self._check_service_health()
        inference_data = await self._run_inference_smoke_test()
        
        is_healthy = health_data.get("status") == "healthy" and inference_data.get("status") == "ok"
        
        if not is_healthy:
            self.consecutive_failures += 1
            logger.warning(f"⚠️ Predictor Stability Check FAILED ({self.consecutive_failures}/{self.max_failures_threshold})")
            
            if self.consecutive_failures >= self.max_failures_threshold:
                await self._trigger_alert(health_data, inference_data)
        else:
            if self.consecutive_failures > 0:
                logger.info("✅ Predictor service recovered.")
                await send_telegram_message(
                    settings.TELEGRAM_CHAT_ID or 0, 
                    "✅ **Olympus Predictor Recovered**\nStandard inference operations resumed."
                )
            self.consecutive_failures = 0
            
        self._is_running = False
        
        return {
            "is_healthy": is_healthy,
            "health": health_data,
            "inference": inference_data,
            "consecutive_failures": self.consecutive_failures
        }

    async def _check_service_health(self) -> Dict[str, Any]:
        """Pings the /health endpoint of the predictor."""
        url = f"{settings.OLYMPUS_PREDICTOR_URL}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "error", "code": resp.status_code, "detail": resp.text}
        except Exception as e:
            return {"status": "unreachable", "detail": str(e)}

    async def _run_inference_smoke_test(self) -> Dict[str, Any]:
        """Performs a real inference call to verify model execution."""
        url = f"{settings.OLYMPUS_PREDICTOR_URL}/predict"
        payload = {"symbol": "XAUUSD", "steps": 1}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    prices = data.get("prices", [])
                    if prices and prices[0] > 0:
                        return {"status": "ok", "last_price": prices[0]}
                    return {"status": "invalid_output", "data": data}
                return {"status": "error", "code": resp.status_code, "detail": resp.text}
        except Exception as e:
            return {"status": "timeout_or_error", "detail": str(e)}

    async def _trigger_alert(self, health: dict, inference: dict):
        """Sends a critical alert to the admin via Telegram."""
        admin_id = settings.TELEGRAM_CHAT_ID or 0
        if not admin_id:
            logger.error("Cannot send stability alert: TELEGRAM_CHAT_ID not set.")
            return

        msg = (
            "🚨 **CRITICAL: Olympus Predictor Unstable**\n\n"
            f"**Health Status**: `{health.get('status')}`\n"
            f"**Inference Status**: `{inference.get('status')}`\n"
            f"**Consecutive Failures**: `{self.consecutive_failures}`\n\n"
            "**Technical Detail**:\n"
            f"Health: `{health.get('detail', 'N/A')}`\n"
            f"Inference: `{inference.get('detail', 'N/A')}`\n\n"
            "Please check service logs immediately."
        )
        await send_telegram_message(admin_id, msg)

# Singleton
stability_observer = StabilityObserver()
