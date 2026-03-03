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
        priority_len = await r.llen("queue:execution:priority")
        commands_len = await r.llen("queue:execution:commands")
        dead_len = await r.llen("queue:exec:dead")
        
        # Kill Switch status
        halted = await r.get("system:kill_switch") == "1"
        
        # Count processed order keys for SETNX observability (approximate)
        _, processed_keys = await r.scan(match="processed_order:*", count=100)
        
        await r.aclose()
        
        return success_response(data={
            "priority_queue": priority_len,
            "default_queue": commands_len,
            "dead_letter_queue": dead_len,
            "system_halted": halted,
            "recently_processed": len(processed_keys)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection failed: {str(e)}")

@router.post("/halt")
async def halt_system():
    """
    Emergency Halt: Stop all execution services from processing new orders.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.set("system:kill_switch", "1")
        await r.publish("system:events", json.dumps({"event": "SYSTEM_HALTED"}))
        await r.aclose()
        return success_response(message="SYSTEM HALTED. All trade executions suspended.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume")
async def resume_system():
    """
    Resume system after emergency halt.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.delete("system:kill_switch")
        await r.publish("system:events", json.dumps({"event": "SYSTEM_RESUMED"}))
        await r.aclose()
        return success_response(message="System resumed. Trade executions enabled.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import json
