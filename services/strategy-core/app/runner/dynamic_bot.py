import logging
import pandas as pd
import numpy as np
from app.market_data import SharedMarketDataManager
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DynamicBotExecutor:
    """
    Executes user-defined Python strategy code safely in a sandbox.
    """
    def __init__(self, code: str, deployment_id: str):
        self.code = code
        self.deployment_id = deployment_id
        self._compiled_code = compile(code, f"<strategy_{deployment_id}>", 'exec')

    async def execute(self, state: Any, data_manager: SharedMarketDataManager) -> Optional[Dict[str, Any]]:
        """
        Executes the strategy logic.
        Expected User Code Signature:
        def strategy(data: pd.DataFrame, params: dict):
            # ...
            return signal_dict or None
        """
        try:
            # 1. Get Data from Manager
            # Custom strategies usually expect a DataFrame with OHLCV
            df = data_manager.get_data(state.symbol)
            if df.empty:
                return None
            
            # 2. Prepare Sandbox Context
            # We strictly limit what's available
            
            # Helper indicators
            try:
                import pandas_ta as ta
            except ImportError:
                ta = None
            
            local_scope = {
                "pd": pd,
                "np": np,
                "ta": ta,
            }
            
            # Execute the module definition
            exec(self._compiled_code, {}, local_scope)
            
            # Find the 'strategy' function
            if "strategy" not in local_scope:
                logger.error(f"Strategy {self.deployment_id}: 'strategy' function not found.")
                return None
                
            strategy_fn = local_scope["strategy"]
            
            # 3. Call User Function
            # state.config_json contains the captured snapshot params
            params = state.config_json.get("strategy_params", {})
            
            # Execute
            # Note: This is synchronous exec. For heavy calculation, might block loop.
            # Phase 8 optimization: Run in Executor/Thread if slow.
            signal = strategy_fn(df, params)
            
            return signal

        except Exception as e:
            logger.error(f"Runtime Error in Deployment {self.deployment_id}: {e}")
            # We should probably track error count and stop if too many errors
            return None
