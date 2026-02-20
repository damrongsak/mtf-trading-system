from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
import logging
import os
import redis.asyncio as redis
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olympus-predictor")

from app.model_engine import HybridPredictor
from app.data_loader import DataLoader
from app.schemas import PredictionRequest, PredictionResponse, TrainingResponse
from fastapi import BackgroundTasks, HTTPException

# Global instances
redis_pool = None
db_pool = None
predictor = None
data_loader = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool, db_pool
    logger.info("Starting Olympus Predictor Service...")
    
    # Initialize Redis
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_pool = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    logger.info(f"Connected to Redis at {redis_url}")

    # Initialize Postgres
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        db_pool = await asyncpg.create_pool(db_url)
        logger.info("Connected to PostgreSQL")
    else:
        logger.warning("DATABASE_URL not set, DB features will be disabled")

    # Initialize Components
    global predictor, data_loader
    predictor = HybridPredictor()
    data_loader = DataLoader(db_pool, redis_pool)
    
    # Load existing models if available
    try:
        predictor.load_models()
        logger.info("Loaded existing models")
    except Exception as e:
        logger.warning(f"Could not load models: {e}")

    yield
    
    # Cleanup
    if redis_pool:
        await redis_pool.close()
        logger.info("Closed Redis connection")
    if db_pool:
        await db_pool.close()
        logger.info("Closed PostgreSQL connection")

app = FastAPI(
    title="Olympus Hybrid Predictor",
    description="Gold Price Forecasting Service using SARIMAX + LSTM",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "olympus-predictor"}

@app.post("/predict", response_model=PredictionResponse)
async def predict_gold(request: PredictionRequest):
    if not predictor.sarimax_model:
        raise HTTPException(status_code=503, detail="Model not trained yet")
        
    try:
        # Fetch latest macro data for context (inference lookback)
        # We need roughly 'lookback' days + steps
        # Also need recent PRICE data to compute technicals (RSI, GARCH, etc.)
        lookback_rows = 200 # Sufficient for GARCH/RSI calculation
        
        gold_task = data_loader.get_gold_data(limit=lookback_rows)
        macro_task = data_loader.get_macro_data(lookback_days=60)
        
        gold_df, macro_df = await asyncio.gather(gold_task, macro_task)
        
        if gold_df.empty:
             raise HTTPException(status_code=503, detail="No Gold data available for inference")
             
        # Compute Technicals on recent price history
        # This adds 'rsi', 'garch_vol', etc. to the dataframe
        gold_df_tech = predictor.feature_engine.compute_technicals(gold_df)
        
        # Merge Technicals into Macro DF (or just combine them)
        # The predictor expects a single 'macro_df' containing ALL exog features (Macro + Tech)
        # We align them on index
        
        # Align indexes (intersection)
        common_idx = gold_df_tech.index.intersection(macro_df.index)
        
        # If macro data is lagging or missing, we might have issues.
        # For inference, we prioritize the LATEST info.
        # If intersection is empty (e.g. macro data delayed), we should ffill/bfill macro to match gold
        
        # Reindex macro to gold index (ffill to propagate last known macro values to current time)
        macro_aligned = macro_df.reindex(gold_df_tech.index).ffill().bfill()
        
        # Combine
        # gold_df_tech has [open, high, low, close, rsi, garch...]
        # macro_aligned has [CL=F, ...]
        combined_context = macro_aligned.join(gold_df_tech[['stoch_k', 'stoch_d', 'stoch_d_smooth', 'williams_r', 'rsi', 'macd', 'macd_signal', 'atr', 'ema_5', 'ema_10', 'garch_vol']])
        
        result = predictor.predict(steps=request.steps, macro_df=combined_context)
        
        return PredictionResponse(
            symbol=request.symbol,
            forecast_date=datetime.now(),
            predictions=result['total'],
            model_version="1.0.0",
            breakdown=result
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train", response_model=TrainingResponse)
async def train_model(background_tasks: BackgroundTasks):
    """Trigger background training"""
    # Fetch data first (fast)
    try:
        # Fetch enough history for training
        # Gold data limited to 50000 rows (~5 years of H1 data)
        df_task = data_loader.get_gold_data(limit=50000)
        macro_task = data_loader.get_macro_data(lookback_days=2000) # ~5 years
        
        df, macro_df = await asyncio.gather(df_task, macro_task)
        
        if df.empty:
             raise HTTPException(status_code=404, detail="No training data found")
             
        # Run training in background to not block
        background_tasks.add_task(predictor.train, df, macro_df)
        
        return TrainingResponse(
            status="started",
            metrics={},
            trained_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Training trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
