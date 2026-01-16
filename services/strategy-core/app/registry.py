
import asyncio
import logging
import os
import importlib
from typing import Optional, Dict, Any
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr
from app.engine.expression_engine import ExpressionEngine
from app.indicators.smc import detect_order_blocks

logger = logging.getLogger(__name__)

class StrategyRegistry:
    _strategies: Dict[str, Any] = {}
    _metadata: Dict[str, Dict] = {}
    _loaded = False

    @classmethod
    def load_strategies(cls):
        """
        Dynamically discovers and registers strategies from the 'strategies' directory.
        Looks for 'strategy.py' in each subdirectory.
        """
        strategies_dir = os.path.join(os.path.dirname(__file__), "strategies")
        
        if not os.path.exists(strategies_dir):
            logger.error(f"Strategies directory not found: {strategies_dir}")
            return

        logger.info(f"Scanning for strategies in: {strategies_dir}")

        for item in os.listdir(strategies_dir):
            strategy_path = os.path.join(strategies_dir, item)
            
            # Check if it's a directory and has strategy.py
            if os.path.isdir(strategy_path) and "strategy.py" in os.listdir(strategy_path):
                try:
                    module_name = f"app.strategies.{item}.strategy"
                    module = importlib.import_module(module_name)
                    
                    # 1. Get Metadata
                    if hasattr(module, "METADATA"):
                        metadata = module.METADATA
                    else:
                        logger.warning(f"Strategy {item} is missing METADATA dict. Skipping.")
                        continue
                        
                    # 2. Get Strategy Function
                    if hasattr(module, "strategy"):
                        func = module.strategy
                        if not asyncio.iscoroutinefunction(func):
                            logger.warning(f"Strategy {item} function is not async. Skipping.")
                            continue
                            
                        # 3. Register
                        # Use directory name upper-cased as ID, or rely on manual mapping?
                        # Convention: Folder 'smc_v1' -> ID 'SMC_V1'
                        strategy_id = item.upper()
                        
                        cls._strategies[strategy_id] = func
                        cls._metadata[strategy_id] = metadata
                        logger.info(f"Registered strategy: {strategy_id}")
                        
                    else:
                        logger.warning(f"Strategy {item} is missing 'async def strategy()'.")
                        
                except Exception as e:
                    logger.error(f"Failed to load strategy {item}: {e}")
                    
        cls._loaded = True

    @classmethod
    def get_strategy(cls, template_id: str):
        if not cls._loaded: cls.load_strategies()
        return cls._strategies.get(template_id)

    @classmethod
    def get_strategy_logic(cls, template_id: str):
        if not cls._loaded: cls.load_strategies()
        return cls._strategies.get(template_id)

    @classmethod
    def get_metadata(cls, template_id: str):
        if not cls._loaded: cls.load_strategies()
        return cls._metadata.get(template_id)

    @classmethod
    def list_templates(cls):
        if not cls._loaded: cls.load_strategies()
        return [{"id": k, **v} for k, v in cls._metadata.items()]

    @classmethod
    def register_custom(cls, template_id: str, code: str, name: str = "Custom Strategy"):
        """
        Dynamically compiles and registers a user-defined strategy.
        WARNING: exec() is used. Ensure code is sandboxed or trusted in production.
        """
        try:
            # 1. Prepare Globals
            allowed_globals = {
                "pd": pd,
                "check_macro_bias": check_macro_bias,
                "check_setup_zone": check_setup_zone,
                "check_trigger": check_trigger,
                "calculate_stop_loss": calculate_stop_loss,
                "calculate_ema": calculate_ema, # Assumes logic imports these? logic.py doesn't export them directly usually
                # Fix: Need to import these calculate_* if they are needed.
                # But for now, let's keep list clean.
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

# Initial Load
StrategyRegistry.load_strategies()



