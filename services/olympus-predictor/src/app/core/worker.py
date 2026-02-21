import logging
import json
import asyncio
import os
import redis.asyncio as redis
import asyncpg
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
        self.db_pool = None
        self._running = False
        
        # Phase 3: Shared Infrastructure
        # Note: We'll initialize these in start() to ensure async loop is ready
        self.store = None
        self.predictor = None
        self.loader = None

    async def _init_infra(self):
        """Initialize all infrastructure components within the async loop"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Connected to Redis")
            
        if not self.db_pool and settings.DATABASE_URL:
            self.db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
            logger.info("Connected to PostgreSQL")
            
        if not self.store:
            self.store = FeatureStore(self.redis)
            
        if not self.predictor:
            self.predictor = HybridPredictor(settings.MODEL_DIR, feature_store=self.store)
            
        if not self.loader:
            self.loader = DataLoader(self.db_pool, self.redis)

    async def start(self):
        logger.info(f"Starting Predictor Training Worker, listening on {self.queue_name}...")
        
        await self._init_infra()
        self._running = True
        
        while self._running:
            try:
                result = await self.redis.brpop(self.queue_name, timeout=5)
                if result:
                    _, message_json = result
                    logger.info(f"Received training task: {message_json}")
                    await self._process_task(message_json)
            except asyncio.CancelledError:
                break
            except redis.ConnectionError as ce:
                logger.error(f"Redis Connection Error: {ce}. Retrying in 5s...")
                self.redis = None
                await asyncio.sleep(5)
                await self._init_infra()
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        if self.redis:
            await self.redis.close()
        if self.db_pool:
            await self.db_pool.close()
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
                # 1. Fetch Data using established loader
                df_gold = await self.loader.get_gold_data(limit=lookback)
                df_macro = await self.loader.get_macro_data(lookback_days=macro_lookback)
                
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
    logging.basicConfig(level=logging.INFO)
    worker = TrainingWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        asyncio.run(worker.stop())
