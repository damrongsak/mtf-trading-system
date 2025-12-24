import logging
import asyncio
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db_context
from app.models.strategy import StrategyModel
from app.engine import StrategyEngine
from app.schemas import ExecutionMode

logger = logging.getLogger(__name__)

class FleetLoader:
    def __init__(self, engine: StrategyEngine):
        self.engine = engine

    async def load_fleet(self):
        """
        Load all active strategies from the database and start them in the engine.
        This allows the Fleet to survive restarts and scale.
        """
        logger.info("FleetLoader: Syncing active strategies from DB...")
        try:
            with get_db_context() as db:
                active_strategies = db.query(StrategyModel).filter(StrategyModel.is_active == True).all()
                
                if not active_strategies:
                    logger.info("FleetLoader: No active strategies found in DB.")
                    return

                count = 0
                for strategy_record in active_strategies:
                    try:
                        # Extract config and merge with record fields
                        # We prioritize DB columns over JSON content for ID/Template
                        config = strategy_record.config_json or {}
                        
                        # Normalize ID to string
                        s_id = str(strategy_record.id)
                        
                        # Merge critical fields
                        config.update({
                            "id": s_id,
                            "template_id": strategy_record.template_id,
                            "broker_account_id": str(strategy_record.broker_account_id),
                            "risk_settings": strategy_record.risk_settings or {},
                            "execution_mode": ExecutionMode.AUTO if strategy_record.is_active else ExecutionMode.MANUAL
                        })
                        
                        # Strategy Engine requires 'symbol' and 'timeframe' in config
                        if "symbol" not in config:
                            logger.warning(f"Strategy {s_id} ({strategy_record.name}) missing 'symbol' in config. Skipping.")
                            continue

                        # Start the strategy (idempotent check inside engine)
                        result = await self.engine.start_strategy(s_id, config)
                        if result.get("status") == "started":
                            count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to load strategy {strategy_record.id}: {e}")
                
                logger.info(f"FleetLoader: Successfully loaded {count} strategies.")

        except Exception as e:
            logger.error(f"FleetLoader critical error: {e}")

