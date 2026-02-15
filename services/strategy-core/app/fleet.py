
import asyncio
import logging
import time
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import SessionLocal
from app.models.strategy import Strategy
from app.models.deployment import Deployment
from app.models.saved_strategy import SavedStrategy
from app.registry import StrategyRegistry
from app.runner.dynamic_bot import DynamicBotExecutor

logger = logging.getLogger(__name__)

class FleetManager:
    """
    Manages the lifecycle and execution of all active strategies (The Fleet).
    In-Memory Fleet Architecture (Option B).
    """
    _instance = None

    def __init__(self):
        self.active_strategies: Dict[str, dict] = {} # Template-based: strategy_id -> context
        self.active_deployments: Dict[str, dict] = {} # Dynamic: deployment_id -> context
        self.last_tick_times: Dict[str, float] = {} # strategy_id/deployment_id -> timestamp
        self.throttle_interval = 2.0 # Minimum seconds between ticks
        self.is_running = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FleetManager()
        return cls._instance

    async def load_fleet(self):
        """
        Loads all active strategies and deployments from the database into memory.
        """
        logger.info("Loading Strategy Fleet...")
        # Force re-scan of strategies
        StrategyRegistry.load_strategies()
        
        self.active_strategies = {}
        self.active_deployments = {}
        
        db = None
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                db = SessionLocal()
                # Test connection
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                break
            except Exception as e:
                if db: db.close()
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts. Aborting fleet load.")
                    return

        try:
            # 1. Load Template Strategies (Legacy/Standard)
            strategies = db.execute(
                select(Strategy).where(Strategy.is_active == True)
            ).scalars().all()
            logger.info(f"FleetManager found {len(strategies)} active strategies in DB.")

            for strategy in strategies:
                try:
                    logic_func = StrategyRegistry.get_strategy(strategy.template_id)
                    if not logic_func:
                        logger.warning(f"Template {strategy.template_id} not found for strategy {strategy.id}")
                        continue

                    context = {
                        "id": str(strategy.id),
                        "type": "TEMPLATE",
                        "name": strategy.name,
                        "fund_id": str(strategy.fund_id),
                        "broker_account_id": str(strategy.broker_account_id),
                        "config": strategy.config_json,
                        "risk_settings": strategy.risk_settings,
                        "logic": logic_func,
                        "symbol": strategy.config_json.get("symbol", "XAU/USD"),
                        "state": {} 
                    }
                    self.active_strategies[str(strategy.id)] = context
                except Exception as e:
                    logger.error(f"Failed to load strategy {strategy.id}: {e}")
            
            # 2. Load Dynamic Deployments
            deployments = db.execute(
                select(Deployment).where(Deployment.status == "ACTIVE")
            ).scalars().all()
            
            for dep in deployments:
                try:
                    # Fetch code from SavedStrategy
                    saved_strat = db.get(SavedStrategy, dep.strategy_id)
                    if not saved_strat:
                        logger.error(f"SavedStrategy {dep.strategy_id} not found for deployment {dep.id}")
                        continue
                        
                    executor = DynamicBotExecutor(saved_strat.code, str(dep.id))
                    
                    context = {
                        "id": str(dep.id),
                        "type": "DYNAMIC",
                        "name": f"Deployment-{dep.id}",
                        "config": dep.config_snapshot,
                        "symbol": dep.stock_symbol,
                        "executor": executor,
                        "is_live": dep.is_live,
                        "state": {}
                    }
                    self.active_deployments[str(dep.id)] = context
                    
                except Exception as e:
                    logger.error(f"Failed to load deployment {dep.id}: {e}")

            logger.info(f"Fleet Loaded: {len(self.active_strategies)} templates, {len(self.active_deployments)} dynamic bots.")
            
        except Exception as e:
            logger.error(f"Error loading fleet: {e}")
        finally:
            if db: db.close()

    def get_active_symbols(self) -> List[str]:
        """Returns unique list of symbols tracked by active strategies."""
        symbols = set(ctx["symbol"] for ctx in self.active_strategies.values())
        symbols.update(ctx["symbol"] for ctx in self.active_deployments.values())
        return list(symbols)
        
    def add_deployment(self, deployment_id: str):
        """Reloads specific deployment from DB (Called by API)"""
        # For simplicity, just reload everything or fetch specific row.
        # MVP: full reload is safe enough if fleet is small. 
        # Better: Single fetch.
        asyncio.create_task(self.load_fleet()) # Async reload

    def remove_deployment(self, deployment_id: str):
        if deployment_id in self.active_deployments:
            del self.active_deployments[deployment_id]

    async def tick(self, data_manager, symbol_filter: str = None):
        """
        Main Loop: Iterates over strategies and deployments.
        """
        if not self.active_strategies and not self.active_deployments:
            return
        
        now = time.time()

        # 1. Tick Template Strategies
        for strat_id, context in self.active_strategies.items():
            if symbol_filter and context["symbol"] != symbol_filter:
                continue
            
            # Throttle check
            last_run = self.last_tick_times.get(strat_id, 0)
            if now - last_run < self.throttle_interval:
                continue

            try:
                # Wrapper for Template Logic
                class StrategyState:
                    def __init__(self, ctx):
                        self.config_json = ctx["config"]
                        self.symbol = ctx["symbol"]
                        self.id = ctx["id"]
                        self.fund_id = ctx.get("fund_id")
                        self.broker_account_id = ctx["broker_account_id"]
                
                state_obj = StrategyState(context)
                result = await context["logic"](state_obj, data_manager)
                self.last_tick_times[strat_id] = now
                
                if result:
                    logger.info(f"TEMPLATE SIGNAL {context['name']}: {result}")
            except Exception as e:
                logger.error(f"Error ticking template {context['name']}: {e}")

        # 2. Tick Dynamic Deployments
        for dep_id, context in self.active_deployments.items():
            if symbol_filter and context["symbol"] != symbol_filter:
                continue
            
            # Throttle check
            last_run = self.last_tick_times.get(dep_id, 0)
            if now - last_run < self.throttle_interval:
                continue

            try:
                 # Wrapper for Dynamic Logic
                class DeploymentState:
                    def __init__(self, ctx):
                        self.config_json = ctx["config"] # Contains {strategy_params: {...}}
                        self.symbol = ctx["symbol"]
                        self.id = ctx["id"]
                
                state_obj = DeploymentState(context)
                result = await context["executor"].execute(state_obj, data_manager)
                self.last_tick_times[dep_id] = now
                
                if result:
                    signal = result.get("signal")
                    logs = result.get("logs")
                    
                    from app.adapters.gateway import gateway_client
                    
                    # 1. Dispatch Logs (Essential Output)
                    if logs:
                        asyncio.create_task(gateway_client.send_strategy_logs(dep_id, logs))

                    # 2. Dispatch Signal (if any)
                    if signal:
                        logger.info(f"DYNAMIC SIGNAL {context['name']} (Live={context['is_live']}): {signal}")
                        
                        # Prepare Payload for execution
                        payload = {
                            "deployment_id": context["id"],
                            "symbol": signal.get("symbol", context["symbol"]),
                            "direction": signal.get("direction"), 
                            "stop_loss": signal.get("stop_loss"),
                            "risk_usd": signal.get("risk_usd"),
                            "reason": signal.get("reason", "Dynamic Strategy Signal"),
                            "meta_data": signal.get("metadata", {})
                        }
                        
                        # Async dispatch
                        asyncio.create_task(gateway_client.execute_signal(payload))
            except Exception as e:
                logger.error(f"Error ticking deployment {context['name']}: {e}")

