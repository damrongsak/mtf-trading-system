import logging
import asyncio
import pandas as pd
import numpy as np
from app.market_data import SharedMarketDataManager
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.analysis.market_regime import MarketRegime

# import vectorbt as vbt
from app import indicators

logger = logging.getLogger(__name__)

class DynamicBotExecutor:
    """
    Executes user-defined Python strategy code safely in a sandbox.
    """
    def __init__(self, code: str, deployment_id: str):
        self.code = code
        self.deployment_id = deployment_id
        self._compiled_code = compile(code, f"<strategy_{deployment_id}>", 'exec')
        self.strategy_fn = self._initialize_strategy()

    def _initialize_strategy(self):
        """Initializes the strategy scope and extracts the strategy function."""
        try:
            import json
            import time
            import datetime
            import vectorbt as vbt
            local_scope = {
                "pd": pd,
                "np": np,
                "vbt": vbt,
                "json": json,
                "time": time,
                "datetime": datetime,
                "indicators": indicators,
                "__builtins__": __builtins__
            }
            # Symmetric scope binding prevents NameError for injected dependencies
            exec(self._compiled_code, local_scope, local_scope)
            if "strategy" not in local_scope:
                logger.error(f"Strategy {self.deployment_id}: 'strategy' function not found.")
                return None
            return local_scope["strategy"]
        except Exception as e:
            logger.error(f"Initialization Error in Deployment {self.deployment_id}: {e}")
            return None

    def calculate_dynamic_risk(self, regime: 'MarketRegime', is_fakeout: bool, base_risk: float = 1.0) -> float:
        """
        Calculates dynamic risk based on market regime and fakeout status.
        This is a placeholder implementation.
        """
        from app.analysis.market_regime import MarketRegime
        if regime == MarketRegime.TRENDING and not is_fakeout:
            return base_risk * 1.2  # Increase risk in strong trends
        elif regime == MarketRegime.RANGE_BOUND and is_fakeout:
            return base_risk * 0.5  # Decrease risk on fakeouts in range-bound markets
        return base_risk

    async def execute(self, state: Any, data_manager: SharedMarketDataManager) -> Dict[str, Any]:
        """
        Executes the strategy logic and standardizes output.
        """
        try:
            if not self.strategy_fn:
                return {"signal": None, "logs": {}}

            # 1. Get Data from Manager
            df = data_manager.get_data(state.symbol)
            if df.empty:
                return {"signal": None, "logs": {}}
            
            # 2. Call User Function
            params = state.config_json.get("strategy_params", {})
            import inspect

            # Determine arguments based on signature
            sig = inspect.signature(self.strategy_fn)
            if len(sig.parameters) == 2:
                param_names = list(sig.parameters.keys())
                if param_names[0] in ['df', 'data']:
                    result_raw = self.strategy_fn(df, params)
                else:
                    result_raw = self.strategy_fn(state, data_manager)
            else:
                result_raw = self.strategy_fn(df, params)

            # Resiliently handle sync vs async results
            if inspect.isawaitable(result_raw):
                result = await result_raw
            else:
                result = result_raw
            
            # Standardize Result
            # result can be: 
            # 1. signal_dict
            # 2. (entries, exits, signal_dict)
            # 3. (entries, exits, signal_dict, logs)
            
            signal_data = None
            log_data = {}
            
            signal_data = None
            log_data = {}
            reason = "Dynamic Manual Tick"
            
            if isinstance(result, tuple):
                if len(result) >= 3:
                    signal_data = result[2]
                if len(result) >= 4:
                    log_data = result[3]
            else:
                signal_data = result
                
            if isinstance(signal_data, dict):
                reason = signal_data.get("reason", reason)

            return {
                "signal": signal_data if isinstance(signal_data, dict) else None,
                "logs": log_data if isinstance(log_data, dict) else {},
                "reason": reason
            }

        except Exception as e:
            logger.error(f"Runtime Error in Deployment {self.deployment_id}: {e}", exc_info=True)
            return {"signal": None, "logs": {"error": str(e)}}
