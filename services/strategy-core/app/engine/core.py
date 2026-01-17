import asyncio
import logging
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from app.adapters.oanda import OandaAdapter
from app.adapters.execution import execution_client
from app.schemas import ExecutionMode
# # from app.adapters.oanda_history import OandaHistoryAdapter
from app.indicators import calculate_ema, calculate_atr, calculate_rsi
from app.indicators import calculate_ema, calculate_atr, calculate_rsi
from app.indicators.smc import detect_order_blocks
from app.adapters.ai_analyst import get_market_sentiment
from app.database import SessionLocal
from app.models.signal_log import SignalLog
from app.models.opportunity_log import OpportunityLog
from app.streaming.subscriber import RedisSubscriber

logger = logging.getLogger(__name__)

from app.market_data import market_data_manager
from app.config_cache import config_cache
from app.registry import StrategyRegistry

class StrategyState:
    def __init__(self, config: dict):
        self.id = config.get("id")
        self.template_id = config.get("template_id")
        self.broker_account_id = config.get("broker_account_id")
        self.symbol = config.get("symbol", "EUR_USD")
        self.timeframe = config.get("timeframe", "M15")
        self.mode = config.get("execution_mode", ExecutionMode.MANUAL)
        self.last_tick_time = None
        # Data is now accessed via market_data_manager using self.symbol

class StrategyEngine:
    def __init__(self):
        self.active_strategies: Dict[str, StrategyState] = {}
        self._history_adapter = None
        
        # Redis Subscriber
        self.subscriber = RedisSubscriber(self.on_candle_event)

        # Plugin Engine
        from app.plugins.plugin_engine import HookManager, PluginLoader
        self.hook_manager = HookManager()
        # Adjusted path: core.py is in app/engine/, plugins is in app/plugins/
        # So we need dirname(dirname(__file__)) to get to 'app/'
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.loader = PluginLoader(self.hook_manager, plugin_dir=os.path.join(base_dir, "plugins"))
        
        # System Hooks
        self.hook_manager.add_action("on_plugin_error", self.handle_plugin_error)

    def handle_plugin_error(self, error_ctx: dict):
        """System-level handler for plugin errors."""
        logger.error(f"🚨 PLUGIN ERROR: {error_ctx}")
        # Could also disable the plugin here for safety
        
    async def start(self):
        """Start the engine components (subscriber)"""
        await self.subscriber.connect()
        # Load Plugins
        await self.load_active_plugins()

    async def load_active_plugins(self):
        """Load all active plugins from DB"""
        from app.database import SessionLocal
        from app.models.plugins import UserPlugin, Plugin
        from sqlalchemy import select

        logger.info("Loading active plugins...")
        db = SessionLocal()
        try:
            query = select(UserPlugin, Plugin).join(Plugin).where(UserPlugin.is_active == True)
            results = db.execute(query).all()
            
            for user_plugin, plugin in results:
                # Context could be richer (DB connection, etc)
                context = {
                    "db": SessionLocal, # Factory
                    "market_data": market_data_manager
                }
                
                success = self.loader.load_plugin_for_user(
                    plugin_id=plugin.id,
                    user_id=str(user_plugin.user_id),
                    context=context,
                    config=user_plugin.config_overrides
                )
                if success:
                    logger.info(f"Activated plugin {plugin.name} for user {user_plugin.user_id}")
                    
        except Exception as e:
            logger.error(f"Error loading plugins: {e}")
        finally:
            db.close()

    async def start_strategy(self, strategy_id: str, config: dict):
        if strategy_id in self.active_strategies:
            return {"status": "already_running"}
        
        # Cache the config
        config['id'] = strategy_id
        config_cache.set_config(strategy_id, config)
        
        logger.info(f"Starting strategy {strategy_id} with template {config.get('template_id')}")
        state = StrategyState(config)
        
        # Subscribe to required channels (via RedisSubscriber)
        symbol = state.symbol
        # In a real shared data model, we'd ensure the *System* is subscribed to this symbol.
        # For now, we just ensure the engine is listening to the Redis channel for this symbol.
        timeframes = ["M5", "M15", "H1", "H4", "D"] 
        channels = [f"market_data:candle:{symbol}:{tf}" for tf in timeframes]
        if self.subscriber:
             await self.subscriber.subscribe(channels)
        
        # Register strategy
        self.active_strategies[strategy_id] = state
        return {"status": "started"}

    async def stop_strategy(self, strategy_id: str):
        if strategy_id in self.active_strategies:
            del self.active_strategies[strategy_id]
            logger.info(f"Strategy {strategy_id} stopped.")
            return {"status": "stopped"}
        return {"status": "not_running"}

    async def on_candle_event(self, channel: str, data: dict):
        """
        Handle incoming candle completion events from Redis.
        Format: market_data:candle:{symbol}:{tf}
        """
        try:
            parts = channel.split(":") 
            if len(parts) < 4: 
                return
            
            symbol = parts[2]
            tf = parts[3]
            
            # HOOK: on_market_data
            # We pass the raw data dict for now, or the standardized one.
            self.hook_manager.do_action("on_market_data", data)
            
            # 1. Update Shared Market Data
            # Note: This is simplified. Realistically, we'd act on specific TFs.
            # Convert dict to DF row
            new_row = pd.DataFrame([data])
            if 'timestamp' in new_row.columns:
                new_row['timestamp'] = pd.to_datetime(new_row['timestamp'])
            
            # We assume market_data_manager handles appending to the correct buffer
            # For MVP, we'll just update the 'M15' (Base) buffer if this is M15
            # Or better, let manager handle it.
            # market_data_manager.update_candle(symbol, tf, new_row) <- hypothetical
            
            # 2. Iterate Strategies
            # 1. Update Shared Market Data (ONCE per tick)
            current_df = market_data_manager.get_data(symbol)
            if current_df.empty:
                market_data_manager.set_data(symbol, new_row)
            else:
                updated_df = pd.concat([current_df, new_row], ignore_index=True)
                if len(updated_df) > 1000:
                    updated_df = updated_df.iloc[-1000:]
                market_data_manager.set_data(symbol, updated_df)
            
            # 2. Iterate Strategies via FleetManager
            from app.fleet import FleetManager
            await FleetManager.get_instance().tick(market_data_manager, symbol_filter=symbol)

        except Exception as e:
            logger.error(f"Error handling candle event {channel}: {e}")

    async def on_tick(self, data: dict):
        """
        Handle incoming tick data from Redis (market_data:{symbol}).
        Triggers strategies that rely on this symbol.
        """
        try:
            # Data format from Oanda Streamer: 
            # {'type': 'PRICE', 'time': '...', 'bids': [...], 'asks': [...], 'instrument': 'EUR_USD'}
            
            if data.get("type") != "PRICE":
                return
            
            symbol = data.get("instrument")
            if not symbol:
                return
            
            # HOOK: on_market_tick (Optional, high frequency)
            # self.hook_manager.do_action("on_market_tick", data)
                
            # Extract Price (using mid price)
            price = (float(data["bid"]) + float(data["ask"])) / 2
            bid = float(data["bid"])
            ask = float(data["ask"])
            timestamp = pd.to_datetime(data["time"])
            
            # 1. Update Manager
            market_data_manager.update_tick(symbol, price, timestamp, bid=bid, ask=ask) 
            
            # 2. Tick Fleet
            from app.fleet import FleetManager
            await FleetManager.get_instance().tick(market_data_manager, symbol_filter=symbol)

        except Exception as e:
            logger.error(f"Error handling tick {data.get('instrument')}: {e}")

    async def _process_strategy_logic(self, strategy_id: str, state: StrategyState):
        """
        Execute the strategy logic template.
        """
        # Get Template Logic
        logic_fn = StrategyRegistry.get_strategy_logic(state.template_id)
        if not logic_fn:
            logger.warning(f"Unknown template {state.template_id} for strategy {strategy_id}")
            return

        # Execute Logic
        try:
            result = await logic_fn(state, market_data_manager)
            
            signal = None
            if isinstance(result, tuple) and len(result) >= 3:
                 # Support for (entries, exits, signal_dict)
                 # We only care about the signal dict for live execution (index 2)
                 signal = result[2]
            elif isinstance(result, dict):
                 signal = result

            if signal:
                await self._execute_signal(strategy_id, state, signal)
        except Exception as e:
            logger.error(f"Error in strategy logic {strategy_id}: {e}")

    async def _execute_signal(self, strategy_id: str, state: StrategyState, signal: dict):
        logger.info(f"Signal for {strategy_id}: {signal}")
        
        # HOOK: filter_signal
        # Allow plugins to modify signal (e.g. filter out, change size hint)
        signal = self.hook_manager.apply_filters("filter_signal", signal, state)
        
        # --- VOLATILITY FILTER (New) ---
        # Calculate ATR to check if market is dead
        # Simplified: Get recent candles, calc ATR.
        try:
            # We need recent data. market_data_manager has it.
            df = market_data_manager.get_data(state.symbol)
            if not df.empty and len(df) > 20: 
                 # Calc ATR(14)
                 high = df['high']
                 low = df['low']
                 close = df['close']
                 atr_series = calculate_atr(high, low, close, window=14)
                 current_atr = atr_series.iloc[-1]
                 
                 # Threshold: Hardcoded 5 pips (0.0005 for forex) or generic?
                 # For XAUUSD, 1.0 is decent.
                 # Let's use a dynamic threshold or config.
                 # For MVP: 0.5 for Gold.
                 min_volatility = 0.5 if "XAU" in state.symbol else 0.0005
                 
                 if current_atr < min_volatility:
                     logger.info(f"Signal BLOCKED by Volatility: ATR {current_atr:.4f} < {min_volatility}")
                     
                     # Log Opportunity
                     try:
                         db = SessionLocal()
                         opp_log = OpportunityLog(
                             symbol=state.symbol,
                             timeframe=state.timeframe,
                             direction=signal['direction'],
                             strategy_name=f"Strategy-{strategy_id}",
                             filter_name="ATR_VOLATILITY",
                             filter_value=float(current_atr),
                             threshold_value=float(min_volatility),
                             reason=f"Low Volatility (ATR < {min_volatility})",
                             meta_data=signal.get('meta_data')
                         )
                         db.add(opp_log)
                         db.commit()
                         db.close()
                     except Exception as ex:
                         logger.error(f"Failed to save OpportunityLog: {ex}")
                         
                     return # SKIP EXECUTION
        except Exception as e:
            logger.warning(f"Volatility check failed: {e}")

        if not signal:
            logger.info(f"Signal for {strategy_id} filtered out by plugin.")
            return

        # --- SENTIMENT CHECK (New) ---
        sentiment_data = None
        # Only check if we are about to trade (AUTO) or notify (MANUAL)
        # For efficiency, maybe only check strictly before 'place_order' or saving signal.
        # Let's check it now to include in the log.
        try:
            sentiment_data = await get_market_sentiment(state.symbol)
        except Exception as e:
            logger.warning(f"Sentiment check failed/skipped: {e}")

        # Block if sentiment opposes direction strong?
        # Threshold: Score < -0.5 for invalidating LONG, Score > 0.5 for invalidating SHORT
        # This is a basic rule. Could be configurable in StrategyConfig.
        is_sentiment_blocked = False
        if sentiment_data:
            s_score = sentiment_data.get("score", 0.0)
            if signal['direction'] == "BULLISH" and s_score < -0.5:
                is_sentiment_blocked = True
                logger.info(f"Signal BLOCKED by Sentiment: Score {s_score} (Bearish) vs Signal Bullish")
            elif signal['direction'] == "BEARISH" and s_score > 0.5:
                is_sentiment_blocked = True
                logger.info(f"Signal BLOCKED by Sentiment: Score {s_score} (Bullish) vs Signal Bearish")

        # --- PERSIST SIGNAL LOG ---
        try:
            db = SessionLocal()
            new_signal = SignalLog(
                symbol=state.symbol,
                timeframe=state.timeframe,
                direction=signal['direction'],
                strategy_name=f"Strategy-{strategy_id}", # Or lookup name
                deployment_id=None, # We don't have deployment ID handy in StrategyState yet, simplistic
                confidence=signal.get('confidence', 0.0),
                price=signal.get('price'),
                reason=signal.get('reason'),
                meta_data=signal.get('meta_data', {}),
                sentiment_score=sentiment_data.get("score") if sentiment_data else None,
                sentiment_reason=sentiment_data.get("reason") if sentiment_data else None
            )
            # Mark if blocked in metadata
            if is_sentiment_blocked:
                if not new_signal.meta_data: new_signal.meta_data = {}
                new_signal.meta_data["blocked_by"] = "sentiment"
            
            db.add(new_signal)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to save SignalLog: {e}")

        if is_sentiment_blocked:
            return # Stop execution

        if state.mode == ExecutionMode.AUTO:
            try:
                # Retrieve current config from Cache (in case Risk settings changed)
                current_config = config_cache.get_config(strategy_id) or {}
                
                # Payload for Execution Service
                order_payload = {
                    "broker_account_id": str(state.broker_account_id), # Passed from Config
                    "symbol": state.symbol,
                    "direction": signal['direction'], # BULLISH/BEARISH
                    "stop_loss": float(signal['stop_loss']) if signal.get('stop_loss') else None,
                    "generated_by": strategy_id,
                    "reason": signal.get("reason", "Strategy Signal")
                }
                
                # HOOK: filter_trade_request
                # Last line of defense before execution
                order_payload = self.hook_manager.apply_filters("filter_trade_request", order_payload)
                
                if not order_payload:
                     logger.warning(f"Trade request filtered out for {strategy_id}")
                     return

                # Send to Execution Service
                # Note: Execution Service 'place_order' adapter might need update to accept this payload
                # Currently it expects 'units'. Execution Service needs to calculate units based on Risk.
                # We need to ensure Execution Service supports `risk_check` or `smart_order`.
                
                # Assuming Execution Service exposes a smart 'execute' endpoint or we calculate here.
                # For Plan consistency: Execution Service calculates lot size.
                # Only if using the new 'Smart Execution' endpoint.
                
                # Let's assume we send this to a new endpoint or the existing one is updated.
                # The existing place_order takes 'units'.
                # We might need to CALCULATE units here if Execution Service doesn't do it yet.
                # Breaking Change: If Execution Service is not updated, this fails.
                
                # Temporary Adapter: Calculate Lot Size Here using Config
                # risk_usd = current_config.get("risk_settings", {}).get("risk_per_trade", 10.0)
                # This logic is best in Execution Service.
                
                response = await execution_client.place_order(order_payload)
                logger.info(f"Executed AUTO order for {strategy_id}: {response}")
                    
            except Exception as e:
                logger.error(f"Execution failed: {e}")

strategy_engine = StrategyEngine()
