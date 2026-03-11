from fastapi import APIRouter, Header, HTTPException, Depends
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from app.core.globals import services
from app.utils.response import success_response
import json

router = APIRouter(prefix="/orchestration", tags=["Orchestration"])
logger = logging.getLogger(__name__)

@router.get("/logs")
async def get_orchestration_logs(limit: int = 50):
    """
    Fetch the latest agent orchestration and pipeline logs from Redis.
    """
    redis = services.get("redis")
    if not redis:
        return success_response(data=[], message="Redis audit logging is currently disabled.")

    try:
        # Fetch from stream
        # XREVRANGE key end start [COUNT count]
        raw_logs = await redis.xrevrange("orchestration.audit.stream", count=limit)
        
        formatted_logs = []
        for log_id, data in raw_logs:
            # Redis stream data is returned as a dict with byte/string keys
            formatted_logs.append({
                "id": log_id,
                **data
            })
            
        return success_response(data=formatted_logs)
    except Exception as e:
        logger.error(f"Failed to fetch orchestration logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipeline/status")
async def get_pipeline_status():
    """
    Get the current state of autonomous pipelines.
    """
    redis = services.get("redis")
    if not redis:
         return success_response(data={"sentiment_to_risk": "DISABLED"})

    try:
        sentiment_key = "sentiment:previous_score:XAUUSD"
        prev_score = await redis.get(sentiment_key)
        
        # Determine health based on last stream entry
        last_entry = await redis.xrevrange("orchestration.audit.stream", count=1)
        last_run = "Never"
        if last_entry:
            last_run = last_entry[0][1].get("timestamp", "Unknown")

        return success_response(data={
            "sentiment_to_risk": {
                "status": "ACTIVE",
                "last_run": last_run,
                "monitored_symbol": "XAUUSD",
                "current_reference_score": float(prev_score) if prev_score else 0.0
            }
        })
    except Exception as e:
        logger.error(f"Failed to fetch pipeline status: {e}")
        return success_response(data={"sentiment_to_risk": "ERROR", "detail": str(e)})

@router.get("/cache/status")
async def get_cache_status():
    """
    Get Semantic Cache statistics and index information.
    """
    redis = services.get("redis")
    advisor = services.get("strategy_advisor")
    
    stats = {
        "hits": 0,
        "misses": 0,
        "total_entries": 0,
        "hit_rate": 0.0
    }
    
    if redis:
        try:
            hits = await redis.get("stats:cache:hit")
            misses = await redis.get("stats:cache:miss")
            stats["hits"] = int(hits) if hits else 0
            stats["misses"] = int(misses) if misses else 0
            
            total = stats["hits"] + stats["misses"]
            if total > 0:
                stats["hit_rate"] = round(stats["hits"] / total, 4)
        except Exception as e:
            logger.error(f"Failed to fetch cache stats from Redis: {e}")

    if advisor and hasattr(advisor, "cache") and advisor.cache.index:
        try:
            # RedisVL SearchIndex.info() returns a dict of index metadata
            info = advisor.cache.index.info()
            stats["total_entries"] = int(info.get("num_docs", 0))
        except Exception as e:
            logger.error(f"Failed to fetch RedisVL index info: {e}")

    return success_response(data=stats)
