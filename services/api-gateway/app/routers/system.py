from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.system_config import SystemConfig
from typing import List, Dict, Any

router = APIRouter()

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
