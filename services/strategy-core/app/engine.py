import asyncio
from typing import Dict, List
from app.adapters.oanda import OandaAdapter
# from app.strategies.base import BaseStrategy # Future: Abstract Base Class
# from app.strategies.mtf_smc import MTF_SMC_Strategy # Future: Concrete Implementation

class StrategyEngine:
    def __init__(self):
        self.active_strategies: Dict[str, asyncio.Task] = {}
        self.data_adapters: Dict[str, OandaAdapter] = {}

    async def start_strategy(self, strategy_id: str, config: dict):
        if strategy_id in self.active_strategies:
            return {"status": "already_running"}
        
        # Initialize Adapter if needed
        data_source_id = config.get("data_source_id")
        if data_source_id not in self.data_adapters:
            try:
                self.data_adapters[data_source_id] = OandaAdapter(data_source_id)
            except Exception as e:
                return {"status": "error", "message": f"Failed to init adapter: {str(e)}"}

        # Create Task
        task = asyncio.create_task(self._run_strategy_loop(strategy_id, config))
        self.active_strategies[strategy_id] = task
        return {"status": "started"}

    async def stop_strategy(self, strategy_id: str):
        if strategy_id in self.active_strategies:
            self.active_strategies[strategy_id].cancel()
            del self.active_strategies[strategy_id]
            return {"status": "stopped"}
        return {"status": "not_running"}

    async def _run_strategy_loop(self, strategy_id: str, config: dict):
        """
        Main loop for a running strategy.
        Fetches data -> Calculates Signal -> Executes Trade
        """
        adapter = self.data_adapters.get(config.get("data_source_id"))
        symbol = config.get("symbol", "EUR_USD")
        timeframe = config.get("timeframe", "M15")

        try:
            while True:
                # 1. Fetch Data
                # candles = adapter.fetch_candles(symbol, timeframe)
                
                # 2. Process Strategy Logic (Placeholder)
                # signal = strategy_logic.analyze(candles)
                
                # 3. Execute (Placeholder)
                # if signal: execution_service.execute(signal)

                await asyncio.sleep(60) # Wait for next candle
        except asyncio.CancelledError:
            print(f"Strategy {strategy_id} stopped.")
        except Exception as e:
            print(f"Strategy {strategy_id} crashed: {e}")
