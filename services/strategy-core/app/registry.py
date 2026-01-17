
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
                    func = None
                    if hasattr(module, "strategy"):
                        func = module.strategy
                    else:
                        logger.warning(f"Strategy {item} is missing 'strategy' function.")
                        continue

                    # 3. Auto-Adapter for Sync Functions (Vectorized)
                    # If func is NOT async, we wrap it.
                    if not asyncio.iscoroutinefunction(func):
                        logger.info(f"Strategy {item} is SYNC (Vectorized). Wrapping in Async Adapter.")
                        
                        # Capture func in closure
                        original_func = func
                        
                        async def wrapper(state, data_manager):
                            """
                            Auto-generated adapter for Vectorized Strategies.
                            Fetches 1 year of data, runs sync logic, returns signal.
                            """
                            try:
                                # 1. Fetch Data (Default 1 Year)
                                import datetime
                                end_date = datetime.datetime.utcnow()
                                start_date = end_date - datetime.timedelta(days=365)
                                
                                # data_manager.get_data usually returns what's in buffer or fetches from DB?
                                # Ideally data_manager should support 'get_history' or similar.
                                # For now, assuming get_data returns a DataFrame.
                                # If data_manager is the StreamManager, it might be limited.
                                # We might need to use fetch_data_from_db logic here or via data_manager.
                                
                                # Using data_manager.get_data(symbol) usually returns the LIVE buffer (limited size).
                                # To get 1 year for a VBT strategy, we need to fetch from DB.
                                # But wrapper runs inside 'strategy-core' service, so we can access DB.
                                
                                from app.backtest import fetch_data_from_db
                                from app.database import SessionLocal
                                from app.models.market import MarketSymbol
                                from app.models.data_source import DataSource
                                
                                # Resolve ID
                                db = SessionLocal()
                                try:
                                    ms = db.query(MarketSymbol).filter(
                                        (MarketSymbol.symbol == state.symbol) | (MarketSymbol.symbol == state.symbol.replace("/", "_"))
                                    ).first()
                                    if not ms:
                                        logger.error(f"MarketSymbol not found for {state.symbol}")
                                        return None
                                    market_symbol_id = ms.id
                                finally:
                                    db.close()
                                
                                # Fetch
                                df = fetch_data_from_db(market_symbol_id, state.timeframe, start_date, end_date)
                                
                                if df.empty:
                                    logger.warning(f"No data for {state.symbol} in wrapper.")
                                    return None
                                    
                                # 2. Run Sync Logic
                                # strategy(data, params) -> entries, exits, signal
                                # or entries, exits
                                
                                # We need default params from metadata if available
                                params = metadata.get("defaults", {})
                                
                                # Call
                                result = original_func(df, params=params)
                                
                                # 3. Extract Signal
                                entries, exits = None, None
                                signal_dict = None
                                
                                if isinstance(result, tuple):
                                    if len(result) >= 3:
                                        entries, exits, signal_dict = result[0], result[1], result[2]
                                    else:
                                        entries, exits = result[0], result[1]
                                else:
                                    # Fallback if just one return? Unlikely for VBT.
                                    pass
                                
                                # If signal_dict is provided directly, use it?
                                # But we should check if the LATEST bar triggered.
                                # VBT logic: returns boolean series.
                                
                                # Check latest bar
                                if entries is not None and not entries.empty:
                                    if bool(entries.iloc[-1]):
                                        if signal_dict: return signal_dict
                                        return {"direction": "BULLISH", "reason": "VBT Entry"}
                                
                                return None

                            except Exception as e:
                                logger.error(f"Error in strategy wrapper for {item}: {e}")
                                return None

                        cls._strategies[strategy_id] = wrapper

                    cls._metadata[strategy_id] = metadata
                    logger.info(f"Registered strategy: {strategy_id}")
                        
                except Exception as e:
                    logger.error(f"Failed to load strategy {item}: {e}")
                    
        cls._loaded = True

    @classmethod
    def reload_strategies(cls):
        """
        Forces a reload of all strategy modules.
        Useful for development (Hot Reload).
        """
        import sys
        
        logger.info("Reloading all strategies...")
        
        # 1. Clear Registry
        cls._strategies.clear()
        cls._strategies_sync.clear()
        cls._metadata.clear()
        cls._loaded = False
        
        # 2. Invalidate Caches (Optional but recommended)
        importlib.invalidate_caches()
        
        # 3. Reload Modules if they exist in sys.modules
        # We need to find modules that start with "app.strategies."
        modules_to_reload = []
        for name, module in sys.modules.items():
            if name.startswith("app.strategies.") and hasattr(module, "strategy"):
                modules_to_reload.append(module)
        
        for module in modules_to_reload:
            try:
                importlib.reload(module)
                logger.info(f"Reloaded module: {module.__name__}")
            except Exception as e:
                logger.error(f"Failed to reload strategy module {module.__name__}: {e}")

        # 4. Re-run Discovery
        cls.load_strategies()
        return True

    @classmethod
    def get_strategy(cls, template_id: str):
        if not cls._loaded: cls.load_strategies()
        return cls._strategies.get(template_id)

    @classmethod
    def get_strategy_sync(cls, template_id: str):
        """Get the synchronous/vectorized version of a strategy (for backtesting)."""
        if not cls._loaded: cls.load_strategies()
        # Return sync if available, else standard (which might be async, careful)
        return cls._strategies_sync.get(template_id)

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



