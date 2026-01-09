from typing import Dict, Any, Optional
from app.plugins.plugin_engine import BasePlugin
import logging

logger = logging.getLogger(__name__)

class RiskGuardrailPlugin(BasePlugin):
    """
    A core safety plugin that acts as a "Kernel Guardrail".
    It intercepts signals and rejects them if they violate hard risk limits.
    """
    
    @property
    def id(self) -> str:
        return "risk-guardrail"
        
    @property
    def name(self) -> str:
        return "Risk Guardrail (Kernel)"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def register(self, hook_manager):
        # Filter: Modifies (or rejects) the signal before it's sent to execution
        hook_manager.register_filter('filter_signal', self.enforce_risk_limits)

    def activate(self):
        logger.info(f"🛡️ RiskGuardrail Activated")

    def deactivate(self):
        logger.info(f"🛡️ RiskGuardrail Deactivated")
        
    def enforce_risk_limits(self, signal: Dict[str, Any], context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Intercepts a trade signal.
        Returns:
            - The signal (if safe)
            - None (if unsafe, effectively blocking the trade)
        """
        if not signal:
            return None
            
        # Get user config for this plugin (if any), or use defaults
        # For a Kernel plugin, we might default to strict rules even without user config
        user_config = context.get('config', {}) if context else {}
        
        # 1. Check Max Risk Per Trade (Default $10.00)
        # Assuming signal has 'stop_loss_amount' or we estimate it.
        # For simplicity in this demo, we check generic 'risk' field if present, or just pass.
        # In a real scenario, we'd calculate Entry - SL * Position Size
        
        # Let's simulate a check on 'metadata'
        meta = signal.get('metadata', {})
        risk_amount = meta.get('estimated_risk', 0.0)
        
        max_allowed_risk = float(user_config.get('max_risk_per_trade', 10.0))
        
        if risk_amount > max_allowed_risk:
            logger.warning(f" [RiskGuardrail] BLOCKED trade {signal.get('symbol')}. Risk ${risk_amount} > Limit ${max_allowed_risk}")
            return None # Block trade
            
        # 2. Check Blacklisted Symbols
        symbol = signal.get('symbol', '')
        blacklist = user_config.get('blacklist', [])
        if symbol in blacklist:
             logger.warning(f" [RiskGuardrail] BLOCKED trade {symbol}. Symbol is blacklisted.")
             return None

        # 3. Check for 'RECKLESS' mode override (just to show config interaction)
        if user_config.get('mode') == 'LOCKDOWN':
             logger.warning(f" [RiskGuardrail] BLOCKED trade {symbol}. System in LOCKDOWN mode.")
             return None

        # If safe, return signal
        logger.info(f" [RiskGuardrail] APPROVED trade {symbol}. Risk ${risk_amount} <= ${max_allowed_risk}")
        return signal
