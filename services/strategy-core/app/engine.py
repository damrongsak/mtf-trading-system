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
from app.smc import detect_order_blocks

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
        from app.streaming.subscriber import RedisSubscriber
        self.subscriber = RedisSubscriber(self.on_candle_event)

    async def start(self):
        """Start the engine components (subscriber)"""
        await self.subscriber.connect()

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
            for s_id, state in self.active_strategies.items():
                if state.symbol == symbol and state.timeframe == tf:
                    # Update local buffer (Legacy support or if Manager is not fully ready)
                    # For now, let's assume we rely on Shared Manager for *Calculation* 
                    # but we trigger on *Event*.
                    
                    # Update shared manager manually here for MVP if Manager is simple dict
                    current_df = market_data_manager.get_data(symbol)
                    if current_df.empty:
                        market_data_manager.set_data(symbol, new_row)
                    else:
                        updated_df = pd.concat([current_df, new_row], ignore_index=True)
                        if len(updated_df) > 1000:
                            updated_df = updated_df.iloc[-1000:]
                        market_data_manager.set_data(symbol, updated_df)

                    # Trigger Logic
                    await self._process_strategy_logic(s_id, state)

        except Exception as e:
            logger.error(f"Error handling candle event {channel}: {e}")

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
            signal = await logic_fn(state, market_data_manager)
            if signal:
                await self._execute_signal(strategy_id, state, signal)
        except Exception as e:
            logger.error(f"Error in strategy logic {strategy_id}: {e}")

    async def _execute_signal(self, strategy_id: str, state: StrategyState, signal: dict):
        logger.info(f"Signal for {strategy_id}: {signal}")
        
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
