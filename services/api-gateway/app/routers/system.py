import os
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.system_config import SystemConfig
from app.utils.response import success_response
from typing import List, Dict, Any

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

@router.get("/config")
def get_system_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get all system configuration (public safe).
    """
    configs = db.query(SystemConfig).all()
    
    # Default fallback if DB is empty (MVP)
    result = {
        "supported_timeframes": ["M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
    }
    
    for c in configs:
        result[c.key] = c.value
        
    return result

@router.get("/queue-health")
async def get_queue_health():
    """
    Get Async Execution Queue Health from Redis.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        vip_len = await r.llen("queue:exec:vip")
        retail_len = await r.llen("queue:exec:retail")
        dead_len = await r.llen("queue:exec:dead")
        
        # Count processed order keys for SETNX observability (approximate)
        _, processed_keys = await r.scan(match="processed_order:*", count=100)
        
        await r.aclose()
        
        return success_response(data={
            "vip_queue": vip_len,
            "retail_queue": retail_len,
            "dead_letter_queue": dead_len,
            "recently_processed": len(processed_keys)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection failed: {str(e)}")
