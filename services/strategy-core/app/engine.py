import asyncio
from typing import Dict, List
from app.adapters.oanda import OandaAdapter
# from app.strategies.base import BaseStrategy # Future: Abstract Base Class
# from app.strategies.mtf_smc import MTF_SMC_Strategy # Future: Concrete Implementation

from app.adapters.execution import execution_client
from app.schemas import ExecutionMode

class StrategyEngine:
    def __init__(self):
        self.active_strategies: Dict[str, asyncio.Task] = {}
        self.data_adapters: Dict[str, OandaAdapter] = {}

    async def start_strategy(self, strategy_id: str, config: dict):
        if strategy_id in self.active_strategies:
            return {"status": "already_running"}
        
        # Initialize Adapter if needed
        data_source_id = "oanda" # config.get("data_source_id") # Default to oanda for now
        # if data_source_id not in self.data_adapters:
        #     try:
        #         self.data_adapters[data_source_id] = OandaAdapter(data_source_id)
        #     except Exception as e:
        #         return {"status": "error", "message": f"Failed to init adapter: {str(e)}"}

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

    async def _calculate_signal(self, strategy_id: str, config: dict):
        """
        Placeholder for fetching data and calculating signal.
        Should return an object or dict if signal exists, else None.
        """
        # return strategy_logic.analyze(...)
        return None

    async def _run_strategy_loop(self, strategy_id: str, config: dict):
        """
        Main loop for a running strategy.
        Fetches data -> Calculates Signal -> Executes Trade
        """
        # adapter = self.data_adapters.get(config.get("data_source_id"))
        symbol = config.get("symbol", "EUR_USD")
        timeframe = config.get("timeframe", "M15")
        
        # Default mode to MANUAL if not specified
        mode = config.get("execution_mode", ExecutionMode.MANUAL)

        try:
            while True:
                # 1. Fetch Data & 2. Process Strategy Logic
                signal = await self._calculate_signal(strategy_id, config)
                
                # 3. Execute
                
                # 3. Execute
                if signal: 
                    if mode == ExecutionMode.AUTO:
                        try:
                            # Construct basic order payload
                            order_data = {
                                "symbol": symbol,
                                "units": 1000, # Default lot
                                "type": "MARKET",
                                "generated_by": strategy_id
                            }
                            await execution_client.place_order(order_data)
                            print(f"Strategy {strategy_id}: Placed AUTO order")
                        except Exception as exec_err:
                            print(f"Strategy {strategy_id}: Execution failed: {exec_err}")
                            
                    elif mode == ExecutionMode.SEMIAUTO:
                        print(f"Strategy {strategy_id}: Signal generated (SEMIAUTO). Notification sent.")
                        
                    else: # MANUAL
                        print(f"Strategy {strategy_id}: Signal generated (MANUAL). Logging only.")

                await asyncio.sleep(60) # Wait for next candle
        except asyncio.CancelledError:
            print(f"Strategy {strategy_id} stopped.")
        except Exception as e:
            print(f"Strategy {strategy_id} crashed: {e}")
