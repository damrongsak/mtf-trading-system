import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, List
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.trade import Trade, TradeStatus
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

    async def run_return_drift_check(self, db: Session) -> Dict[str, Any]:
        """
        Calculates KL Divergence between historical and recent trade returns.
        High KLD (> 0.5) indicates performance drift / market regime shift.
        """
        logger.info("📊 Running Return Drift Check (KL Divergence)...")
        
        try:
            # 1. Fetch Reference returns (Long-term: e.g., last 500 trades)
            ref_trades = db.query(Trade.pnl_usd).filter(
                Trade.status == TradeStatus.CLOSED,
                Trade.pnl_usd.isnot(None)
            ).order_by(Trade.exit_timestamp.desc()).limit(500).all()
            
            if len(ref_trades) < 50:
                return {"status": "insufficient_data", "count": len(ref_trades)}
                
            ref_returns = np.array([float(t[0]) for t in ref_trades])
            
            # 2. Fetch Recent returns (Short-term: e.g., last 50 trades)
            recent_returns = ref_returns[:50]
            historical_returns = ref_returns[50:]
            
            if len(recent_returns) < 20: # Minimum to form a distribution
                return {"status": "insufficient_recent_data", "count": len(recent_returns)}

            # 3. Binning (Normalization to Probability Distribution)
            # We use common bins for both to compare apples to apples
            # Returns are USD-based, so we might want to normalize by risk if available, 
            # but pnl_usd is the current source of truth for distribution.
            bins = np.linspace(np.min(ref_returns), np.max(ref_returns), 11) # 10 bins
            
            p_hist, _ = np.histogram(historical_returns, bins=bins, density=True)
            p_recent, _ = np.histogram(recent_returns, bins=bins, density=True)
            
            # Laplace Smoothing (add small epsilon to avoid div by zero/infinity)
            epsilon = 1e-10
            p_hist += epsilon
            p_recent += epsilon
            
            # Normalize to 1.0
            p_hist /= np.sum(p_hist)
            p_recent /= np.sum(p_recent)
            
            # 4. Calculate Kullback-Leibler Divergence
            # D_KL(Recent || Historical) - How much 'Recent' differs from 'Historical'
            kl_div = np.sum(p_recent * np.log(p_recent / p_hist))
            
            is_drifting = kl_div > 0.5 # Institutional standard for "Significant Drift"
            
            logger.info(f"KLD: {kl_div:.4f} (Drift: {is_drifting})")
            
            return {
                "status": "ok",
                "kl_divergence": round(float(kl_div), 4),
                "is_drifting": is_drifting,
                "recent_avg_pnl": round(float(np.mean(recent_returns)), 2),
                "hist_avg_pnl": round(float(np.mean(historical_returns)), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate return drift: {e}", exc_info=True)
            return {"status": "error", "detail": str(e)}

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
