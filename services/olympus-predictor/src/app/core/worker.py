import logging
import json
import asyncio
import os
import redis.asyncio as redis
from src.app.domain.models import HybridPredictor
from src.app.infrastructure.data_loader import DataLoader
from src.app.infrastructure.feature_store import FeatureStore
from src.app.core.config import settings

logger = logging.getLogger("olympus-predictor.worker")

class TrainingWorker:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.queue_name = "queue:predictor:training"
        self.redis = None
        self._running = False
        
        # Phase 3: Shared Infrastructure
        self.store = FeatureStore()
        self.predictor = HybridPredictor(settings.MODEL_DIR, feature_store=self.store)

    async def start(self):
        logger.info(f"Starting Predictor Training Worker, listening on {self.queue_name}...")
        self._running = True
        
        while self._running:
            try:
                if not self.redis:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
                
                result = await self.redis.brpop(self.queue_name, timeout=5)
                if result:
                    _, message_json = result
                    logger.info(f"Received training task: {message_json}")
                    # Offload to a task to allow concurrent training if needed, 
                    # but usually training is resource intensive, so maybe serial is better? 
                    # Let's do serial for now to avoid OOM.
                    await self._process_task(message_json)
            except asyncio.CancelledError:
                break
            except redis.ConnectionError as ce:
                logger.error(f"Redis Connection Error: {ce}. Retrying in 5s...")
                self.redis = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        if self.redis:
            await self.redis.close()
        logger.info("Predictor Training Worker stopped.")

    async def _process_task(self, message_json: str):
        try:
            task_data = json.loads(message_json)
            job_id = task_data.get("job_id")
            symbol = task_data.get("symbol", "XAUUSD")
            lookback = task_data.get("lookback", 2000)
            macro_lookback = task_data.get("macro_lookback", 59)
            
            logger.info(f"Processing Job {job_id}: Training {symbol}")
            
            # Update job status in Redis
            await self.redis.set(f"job:{job_id}:status", "processing", ex=3600)
            
            try:
                loader = DataLoader()
                # 1. Fetch Data
                df_gold = await loader.get_gold_data(symbol=symbol, days=lookback)
                df_macro = await loader.get_macro_data(days=macro_lookback)
                
                # 2. Train Model
                result = await self.predictor.train(df_gold, macro_df=df_macro)
                
                # 3. Save Results
                await self.redis.set(f"job:{job_id}:status", "completed", ex=3600)
                await self.redis.set(f"job:{job_id}:result", json.dumps(result), ex=3600)
                logger.info(f"Job {job_id} completed successfully.")
                
            except Exception as biz_e:
                logger.error(f"Training failed for job {job_id}: {biz_e}")
                await self.redis.set(f"job:{job_id}:status", "failed", ex=3600)
                await self.redis.set(f"job:{job_id}:error", str(biz_e), ex=3600)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received in training queue: {message_json}")
        except Exception as e:
            logger.error(f"Unexpected error in _process_task: {e}", exc_info=True)

if __name__ == "__main__":
    # Simple standalone execution logic
    import sys
    logging.basicConfig(level=logging.INFO)
    worker = TrainingWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        asyncio.run(worker.stop())
