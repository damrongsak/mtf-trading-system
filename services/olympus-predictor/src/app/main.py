from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
import redis.asyncio as redis
import asyncpg
from datetime import datetime
from typing import Optional

from src.app.core.config import settings
from src.app.core.logging import setup_logging
from src.app.domain.models import HybridPredictor
from src.app.infrastructure.data_loader import DataLoader
from src.app.infrastructure.feature_store import FeatureStore
from src.app.api.schemas import (
    PredictionRequest, PredictionResponse, 
    TrainRequest, TrainResponse, JobStatusResponse,
    SignalResponse, BatchPredictionRequest, BatchPredictionResponse
)
from src.app.core.queue import task_queue
import logging

setup_logging()
logger = logging.getLogger("olympus-predictor")

# Global instances
db_pool = None
redis_client = None
predictor = None
data_loader = None

# Mock user for internal consistency (standard MTF pattern)
async def get_current_user():
    return {"id": "internal-admin"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client, predictor, data_loader
    logger.info("Initializing Olympus Predictor (Phase 3 Infrastructure)...")
    
    # Initialize Infrastructure
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    if settings.DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"PostgreSQL Connection Failed: {e}")
    
    feature_store = FeatureStore(redis_client)
    data_loader = DataLoader(db_pool, redis_client)
    predictor = HybridPredictor(model_dir=settings.MODEL_DIR, feature_store=feature_store)
    
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
    version="2.1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    health_status = {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {
            "redis": "unknown",
            "postgresql": "unknown",
            "models_loaded": False
        }
    }
    
    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            health_status["dependencies"]["redis"] = "connected"
        else:
            health_status["dependencies"]["redis"] = "not_initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check PostgreSQL
    try:
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            health_status["dependencies"]["postgresql"] = "connected"
        else:
            health_status["dependencies"]["postgresql"] = "not_initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["dependencies"]["postgresql"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Models
    if predictor and predictor.sarimax_model and predictor.lstm_model:
        health_status["dependencies"]["models_loaded"] = True
    else:
        health_status["status"] = "degraded"

    if health_status["status"] == "degraded":
        # If any critical component is missing, we are not fully healthy
        pass 

    return health_status

@app.post("/predict", response_model=PredictionResponse)
async def predict(req: PredictionRequest):
    if not predictor.sarimax_model:
        raise HTTPException(status_code=503, detail="Model not trained")
        
    try:
        # Fetch context data
        gold_df = await data_loader.get_gold_data(limit=100)
        macro_df = await data_loader.get_macro_data(lookback_days=settings.MACRO_LOOKBACK_DAYS if hasattr(settings, 'MACRO_LOOKBACK_DAYS') else 59)
        
        if gold_df.empty:
             raise HTTPException(status_code=503, detail="No market data available")
             
        # Compute technicals for inference
        df_tech = await predictor.feature_engine.compute_technicals(gold_df)
        
        # Align macro to gold index
        macro_aligned = macro_df.reindex(df_tech.index).ffill().bfill()
        
        # Combined context
        combined_context = macro_aligned.join(df_tech, rsuffix='_tech') 
        
        last_price = gold_df['close'].iloc[-1]
        
        result = await predictor.predict(
            steps=req.steps, 
            macro_df=combined_context, 
            last_price=last_price
        )
        
        return PredictionResponse(
            symbol=req.symbol,
            forecast_date=datetime.now(),
            prices=result['prices'],
            sigma_lr=result['sigma_lr'],
            model_version="2.1.0-alpha",
            breakdown=result
        )
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(req: BatchPredictionRequest):
    """
    Batch Inference for multiple symbols.
    Optimization: Shares macro feature calculation overhead.
    """
    if not predictor.sarimax_model:
        raise HTTPException(status_code=503, detail="Model not trained")
        
    try:
        # Optimization: Fetch Macro data ONCE for the entire batch
        macro_df = await data_loader.get_macro_data(lookback_days=settings.MACRO_LOOKBACK_DAYS if hasattr(settings, 'MACRO_LOOKBACK_DAYS') else 59)
        results = {}

        for symbol in req.symbols:
            try:
                # Fetch gold data (currently only XAUUSD supported in data_loader)
                gold_df = await data_loader.get_gold_data(limit=100)
                if gold_df.empty:
                    continue
                
                df_tech = await predictor.feature_engine.compute_technicals(gold_df)
                macro_aligned = macro_df.reindex(df_tech.index).ffill().bfill()
                combined_context = macro_aligned.join(df_tech, rsuffix='_tech') 
                last_price = gold_df['close'].iloc[-1]
                
                pred = await predictor.predict(
                    steps=req.steps, 
                    macro_df=combined_context, 
                    last_price=last_price
                )
                
                results[symbol] = PredictionResponse(
                    symbol=symbol,
                    forecast_date=datetime.now(),
                    prices=pred['prices'],
                    sigma_lr=pred['sigma_lr'],
                    model_version="2.1.0-alpha",
                    breakdown=pred
                )
            except Exception as se:
                logger.error(f"Batch prediction failed for {symbol}: {se}")
                
        return BatchPredictionResponse(results=results)
    except Exception as e:
        logger.exception("Batch prediction pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signal", response_model=SignalResponse)
async def get_signal(
    req: PredictionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a Confidence-Weighted Signal for Strategy Alignment.
    Phase 4: Creative Alpha integration.
    """
    try:
        # 1. Pipeline: Context Fetch -> Predict -> Signal Generation
        gold_df = await data_loader.get_gold_data(limit=1000)
        macro_df = await data_loader.get_macro_data(lookback_days=settings.MACRO_LOOKBACK)
        
        last_price = gold_df['close'].iloc[-1]
        
        # 2. Predict
        prediction = await predictor.predict(
            steps=req.steps, 
            macro_df=macro_df, 
            last_price=last_price
        )
        
        # 3. Generate Signal
        signal = await predictor.generate_signal(prediction)
        return SignalResponse(**signal)
        
    except Exception as e:
        logger.exception("Signal generation failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train", response_model=TrainResponse)
async def train(
    req: TrainRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger model training.
    Phase 3: Now asynchronous. Returns a job_id.
    """
    try:
        job_id = await task_queue.push_training_job(
            symbol=req.symbol,
            lookback=req.lookback,
            macro_lookback=req.macro_lookback
        )
        return TrainResponse(
            status="queued",
            message=f"Training job {job_id} has been queued.",
            job_id=job_id,
            trained_at=datetime.now()
        )
    except Exception as e:
        logger.exception("Training job queuing failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/train/status/{job_id}", response_model=JobStatusResponse)
async def get_train_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check the status of a training job."""
    try:
        status_data = await task_queue.get_job_status(job_id)
        if status_data["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Job not found")
        return JobStatusResponse(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
