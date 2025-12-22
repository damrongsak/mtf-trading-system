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

class StrategyState:
    def __init__(self, config: dict):
        self.config = config
        self.symbol = config.get("symbol", "EUR_USD")
        self.timeframe = config.get("timeframe", "M15")
        self.mode = config.get("execution_mode", ExecutionMode.MANUAL)
        self.data: Dict[str, pd.DataFrame] = {} # Map timeframe -> DataFrame
        self.last_tick_time = None

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
        
        logger.info(f"Starting strategy {strategy_id} with config: {config}")
        state = StrategyState(config)
        
        # Subscribe to required channels (Base + Trend + Macro)
        symbol = state.symbol
        timeframes = ["M5", "M15", "H1", "H4", "D"] # Subscribe to all relevant for now
        
        channels = [f"market_data:candle:{symbol}:{tf}" for tf in timeframes]
        if self.subscriber:
             await self.subscriber.subscribe(channels)
        
        # Initial data fetch (Warmup)
        try:
            # Resolving ID and fetching data requires sync DB operations
            from app.database import SessionLocal
            from app.utils.helpers import resolve_market_symbol_id
            from app.backtest import fetch_data_from_db
            
            def load_initial_data():
                db = SessionLocal()
                try:
                    ms_id = resolve_market_symbol_id(db, state.symbol)
                    if not ms_id:
                        raise ValueError(f"MarketSymbol not found for {state.symbol}")
                    
                    # Determine range: last 500 candles usually sufficient for warmup
                    # We need to approximate start date based on count and timeframe.
                    # Or fetch_data_from_db logic needs adaptation for 'count'.
                    # For now, let's fetch last 30 days which covers M15 500 candles easily.
                    end_date = datetime.utcnow()
                    start_date = end_date - pd.Timedelta(days=30)
                    
                    df = fetch_data_from_db(ms_id, state.timeframe, start_date, end_date)
                    
                    # Limit to last 500
                    if not df.empty and len(df) > 500:
                       df = df.iloc[-500:]
                    return df
                finally:
                    db.close()

            # Run in executor to avoid blocking async loop
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, load_initial_data)
            
            state.data[state.timeframe] = df
            self.active_strategies[strategy_id] = state
            logger.info(f"Strategy {strategy_id} started. Loaded {len(df)} candles.")
            return {"status": "started"}
        except Exception as e:
            logger.error(f"Failed to start strategy: {e}")
            return {"status": "error", "message": str(e)}

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
            # expected: market_data, candle, symbol, timeframe
            if len(parts) < 4: 
                return
            
            symbol = parts[2]
            tf = parts[3]
            
            # Update state for all relevant strategies
            for s_id, state in self.active_strategies.items():
                if state.symbol == symbol: # match symbol
                    # Update local buffer
                    if tf not in state.data:
                        state.data[tf] = pd.DataFrame() # Initialize if missing
                    
                    # Append new candle
                    # data is the candle dict. format to DF row.
                    new_row = pd.DataFrame([data])
                    new_row['timestamp'] = pd.to_datetime(new_row['timestamp'])
                    if 'timestamp' in state.data[tf].columns:
                         # Append
                         state.data[tf] = pd.concat([state.data[tf], new_row], ignore_index=True)
                    else:
                         state.data[tf] = new_row
                         
                    # Keep buffer size manageable (e.g. 500)
                    if len(state.data[tf]) > 1000:
                        state.data[tf] = state.data[tf].iloc[-1000:]
                        
                    # Trigger Logic if this is the "Base" timeframe (e.g. M15 or M5)
                    if tf == state.timeframe:
                         # Logic Check
                         signal = await self._calculate_signal(s_id, state)
                         if signal:
                             await self._execute_signal(s_id, state, signal)
                             
        except Exception as e:
            logger.error(f"Error handling candle event {channel}: {e}")

    async def on_tick(self, tick_data: dict):
        """
        Ingest a tick, update state, and trigger signal check.
        """
        symbol = tick_data.get("instrument").replace("_", "/") # Normalize
        price = (tick_data['bid'] + tick_data['ask']) / 2
        time = tick_data['time']

        for s_id, state in self.active_strategies.items():
            if state.symbol == symbol or state.symbol.replace("_", "/") == symbol:
                await self._process_tick(s_id, state, price, time)

    async def _process_tick(self, strategy_id: str, state: StrategyState, price: float, time: str):
        # resample logic is complex. For now, we'll append the tick as a 'close' to a temporary row
        # and see if it triggers logic. 
        # A proper implementation would bucket into candles. 
        # Here we will assume we check Logic every time, but valid signals require candle close.
        # Simplification: We blindly append a new row or update the last row?
        
        # Let's just update the last row's Close price to current price (Ghost Candle)
        df = state.data[state.timeframe]
        if df.empty:
            return

        # Update last row (representing current forming candle)
        # Note: This is a hack. Real implementation needs proper timestamp management.
        df.iloc[-1, df.columns.get_loc('close')] = price
        
        # Run Signal Logic
        signal = await self._calculate_signal(strategy_id, state)
        
        if signal:
             await self._execute_signal(strategy_id, state, signal)

    async def _calculate_signal(self, strategy_id: str, state: StrategyState):
        """
        Core Logic. Returns signal dict or None.
        """
        from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection
        
        # Require Base Timeframe data
        if state.timeframe not in state.data:
            return None
            
        df_base = state.data[state.timeframe]
        if len(df_base) < 100: # Need enough history
            return None

        # 0. MTF Handling (Reactive)
        # Try to get H1/H4 from state directly (Event-Driven)
        df_h1 = state.data.get("H1")
        df_h4 = state.data.get("H4")
        
        # Fallback: if H1/H4 missing (not subscribed or startup), try resampling
        try:
            if df_h1 is None or len(df_h1) < 50:
                 df_h1 = df_base.set_index('timestamp').resample('1h').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
                }).dropna().reset_index()
            
            if df_h4 is None or len(df_h4) < 50:
                df_h4 = df_base.set_index('timestamp').resample('4h').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
                }).dropna().reset_index()
                
        except Exception as e:
            logger.warning(f"Resampling fallback failed: {e}")
            return None

        # 1. Macro Bias (Rule A)
        bias = check_macro_bias(df_h4)
        if bias == SignalDirection.NEUTRAL:
            return None
            
        # 2. Setup Zone (Rule B)
        # Check if price is in H1 Order Block of valid direction
        if not check_setup_zone(df_h1, bias):
            return None
            
        # 3. Trigger (Rule C)
        # Check M15 candle trigger
        if not check_trigger(df_m15, bias):
             return None
             
        # 4. Stop Loss (Rule D)
        stop_loss = calculate_stop_loss(df_m15, bias)
        
        return {
            "direction": bias.value,
            "stop_loss": stop_loss,
            "reason": f"SMC Entry: {bias.value} Bias + OB + Trigger"
        }

    async def _execute_signal(self, strategy_id: str, state: StrategyState, signal: dict):
        logger.info(f"Signal for {strategy_id}: {signal}")
        
        # Debounce/One-shot logic needed? (Don't buy 100 times per minute)
        # We can store 'last_trade_time' in state.
        
        if state.mode == ExecutionMode.AUTO:
            try:
                # Safety Guardrail: Check if live trading is explicitly enabled via env var
                live_trading_enabled = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
                
                order_data = {
                    "symbol": state.symbol,
                    "units": 1000 if signal['direction'] == 'BULLISH' else -1000,
                    "type": "MARKET",
                    "generated_by": strategy_id
                }
                
                if live_trading_enabled:
                    response = await execution_client.place_order(order_data)
                    logger.info(f"Executed AUTO order for {strategy_id}: {response}")
                else:
                    logger.info(f"Skipping execution for {strategy_id}: LIVE_TRADING_ENABLED is False. Signal: {signal}")
                    
            except Exception as e:
                logger.error(f"Execution failed: {e}")

strategy_engine = StrategyEngine()
