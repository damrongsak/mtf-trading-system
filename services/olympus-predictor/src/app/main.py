from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
import redis.asyncio as redis
import asyncpg
from datetime import datetime

from src.app.core.config import settings
from src.app.core.logging import setup_logging
from src.app.domain.models import HybridPredictor
from src.app.infrastructure.data_loader import DataLoader
from src.app.api.schemas import PredictionRequest, PredictionResponse, TrainingResponse
import logging

setup_logging()
logger = logging.getLogger("olympus-predictor")

# Global instances
db_pool = None
redis_client = None
predictor = None
data_loader = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client, predictor, data_loader
    logger.info("Initializing Olympus Predictor (New Structure)...")
    
    # Initialize Infrastructure
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    if settings.DATABASE_URL:
        db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
        logger.info("Connected to PostgreSQL")
    
    data_loader = DataLoader(db_pool, redis_client)
    predictor = HybridPredictor(model_dir=settings.MODEL_DIR)
    
    # Load Models
    try:
        predictor.load_models()
        logger.info("Models loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load models on startup: {e}")
        
    yield
    
    # Cleanup
    if redis_client:
        await redis_client.close()
    if db_pool:
        await db_pool.close()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(req: PredictionRequest):
    if not predictor.sarimax_model:
        raise HTTPException(status_code=503, detail="Model not trained")
        
    try:
        # Fetch context data
        gold_df = await data_loader.get_gold_data(limit=100)
        macro_df = await data_loader.get_macro_data(lookback_days=30)
        
        if gold_df.empty:
             raise HTTPException(status_code=503, detail="No market data available")
             
        # Compute technicals for inference
        df_tech = predictor.feature_engine.compute_technicals(gold_df)
        
        # Align macro to gold index
        macro_aligned = macro_df.reindex(df_tech.index).ffill().bfill()
        
        # Combined context: join everything, predictor will pick what it needs
        combined_context = macro_aligned.join(df_tech, rsuffix='_tech') 
        # Note: we might need to handle column name collisions if exog features overlap
        
        last_price = gold_df['close'].iloc[-1]
        
        result = predictor.predict(
            steps=req.steps, 
            macro_df=combined_context, 
            last_price=last_price
        )
        
        return PredictionResponse(
            symbol=req.symbol,
            forecast_date=datetime.now(),
            predictions=result['prices'],
            model_version="2.0.0",
            breakdown=result
        )
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train", response_model=TrainingResponse)
async def train(background_tasks: BackgroundTasks):
    try:
        # Fetch training data
        gold_df = await data_loader.get_gold_data(limit=50000)
        macro_df = await data_loader.get_macro_data(lookback_days=59)
        
        if gold_df.empty:
            raise HTTPException(status_code=404, detail="No training data")
            
        # Offload to background
        background_tasks.add_task(predictor.train, gold_df, macro_df)
        
        return TrainingResponse(
            status="started",
            metrics={},
            trained_at=datetime.now()
        )
    except Exception as e:
        logger.exception("Training trigger failed")
        raise HTTPException(status_code=500, detail=str(e))
