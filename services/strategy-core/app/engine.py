import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from app.adapters.oanda import OandaAdapter
from app.adapters.execution import execution_client
from app.schemas import ExecutionMode
from app.adapters.oanda_history import OandaHistoryAdapter
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

    @property
    def history_adapter(self):
        if not self._history_adapter:
            # Import here to avoid circular dependencies if any, and lazy load
            # Note: OandaHistoryAdapter init connects to DB.
            self._history_adapter = OandaHistoryAdapter()
        return self._history_adapter

    async def start_strategy(self, strategy_id: str, config: dict):
        if strategy_id in self.active_strategies:
            return {"status": "already_running"}
        
        logger.info(f"Starting strategy {strategy_id} with config: {config}")
        state = StrategyState(config)
        
        # Initial data fetch (Warmup)
        # We need M15 for execution, and H1/H4 for specific strategies if implemented
        # For simplicity MVP, we just fetch M15
        try:
            # Run in executor to avoid blocking async loop
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: self.history_adapter.fetch_candles_range(
                symbol=state.symbol,
                timeframe=state.timeframe,
                count=500
            ))
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
        
        df_m15 = state.data[state.timeframe]
        
        if len(df_m15) < 200:
            return None
            
        # 0. MTF Resampling
        # Resample M15 to H1 and H4
        try:
            # Assumes index is DatetimeIndex
            df_h1 = df_m15.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            df_h4 = df_m15.resample('4h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
        except Exception as e:
            logger.warning(f"Resampling failed: {e}")
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
