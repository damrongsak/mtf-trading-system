
import asyncio
import logging
from typing import Optional, Dict
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr
from app.engine.expression_engine import ExpressionEngine
from app.indicators.smc import detect_order_blocks
from app.strategies.volatility_breakout.strategy import strategy as volatility_breakout_strategy
from app.strategies.smc_v1.strategy import strategy as smc_v1_strategy
from app.strategies.macd_cross_v1.strategy import strategy as macd_cross_strategy
from app.strategies.ema_rsi_v1.strategy import strategy as ema_rsi_strategy
from app.strategies.alpha_engine_v1.strategy import strategy as alpha_engine_strategy
from app.strategies.hybrid_alpha_v1.strategy import strategy as hybrid_alpha_strategy

logger = logging.getLogger(__name__)

# --- Template Functions ---
# Strategies are now imported from their respective modules


class StrategyRegistry:
    _strategies = {
        "SMC_V1": smc_v1_strategy,
        "MACD_CROSS_V1": macd_cross_strategy,
        "EMA_RSI_V1": ema_rsi_strategy,
        "ALPHA_ENGINE_V1": alpha_engine_strategy,
        "HYBRID_ALPHA_V1": hybrid_alpha_strategy,
        "STRAT_VOL_BREAKOUT_V1": volatility_breakout_strategy
    }
    
    _metadata = {
        "SMC_V1": {
            "name": "Smart Money Concepts V1",
            "description": "MTF Analysis with Order Blocks and FVGs",
            "defaults": {} 
        },
        "MACD_CROSS_V1": {
            "name": "MACD Crossover",
            "description": "Standard Momentum Strategy",
            "defaults": {}
        },
        "EMA_RSI_V1": {
            "name": "Bias Buy/Sell (EMA + RSI)",
            "description": "Trend Following (EMA200) with Counter-Trend Entry (RSI)",
            "defaults": {
                "ema_period": 200,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            }
        },
        "ALPHA_ENGINE_V1": {
            "name": "Athena Alpha Engine",
            "description": "Generic Formula Execution",
            "defaults": {
                "formula": "rsi(close, 14)",
                "threshold_long": 30,
                "condition_long": "lt",
                "threshold_short": 70,
                "condition_short": "gt"
            }
        },
        "HYBRID_ALPHA_V1": {
            "name": "Hybrid (Momentum + SMC)",
            "description": "Statistical Momentum Filter with Order Block Entry",
            "defaults": {
                "alpha_threshold": 0.8
            }
        },
        "STRAT_VOL_BREAKOUT_V1": {
            "name": "Volatility Breakout V1",
            "description": "Compression Breakout Strategy with AI Metadata",
            "defaults": {
                "atr_period": 14,
                "atr_smooth_period": 20,
                "adr_period": 20,
                "keltner_mult": 2.0
            }
        }
    }

    @classmethod
    def get_strategy(cls, template_id: str):
        return cls._strategies.get(template_id)

    @classmethod
    def get_strategy_logic(cls, template_id: str):
        return cls._strategies.get(template_id)

    @classmethod
    def get_metadata(cls, template_id: str):
        return cls._metadata.get(template_id)

    @classmethod
    def list_templates(cls):
        return [{"id": k, **v} for k, v in cls._metadata.items()]

    @classmethod
    def register_custom(cls, template_id: str, code: str, name: str = "Custom Strategy"):
        """
        Dynamically compiles and registers a user-defined strategy.
        WARNING: exec() is used. Ensure code is sandboxed or trusted in production.
        """
        try:
            # 1. Prepare Globals
            # We allow basic imports and app modules
            allowed_globals = {
                "pd": pd,
                "check_macro_bias": check_macro_bias,
                "check_setup_zone": check_setup_zone,
                "check_trigger": check_trigger,
                "calculate_stop_loss": calculate_stop_loss,
                "calculate_ema": calculate_ema,
                "calculate_rsi": calculate_rsi,
                "calculate_macd": calculate_macd,
                "SignalDirection": SignalDirection,
                "logger": logger
            }
            
            # 2. Compile
            local_scope = {}
            exec(code, allowed_globals, local_scope)
            
            # 3. Extract Function
            if "strategy" not in local_scope:
                raise ValueError("Code must define an async function named 'strategy(state, data_manager)'")
            
            func = local_scope["strategy"]
            if not asyncio.iscoroutinefunction(func):
                 raise ValueError("'strategy' function must be async")

            # 4. Register
            cls._strategies[template_id] = func
            cls._metadata[template_id] = {
                "name": name,
                "description": "User defined custom strategy",
                "defaults": {}
            }
            logger.info(f"Registered custom strategy {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compile custom strategy {template_id}: {e}")
            raise e


