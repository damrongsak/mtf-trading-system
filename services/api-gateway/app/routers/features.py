from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from app.streaming.feature_cache import feature_cache
from app.utils.response import success_response
from app.schemas.response import APIResponse

router = APIRouter(tags=["data"])

@router.get("/features")
async def get_latest_features():
    """
    Returns the latest technical features for all active symbols.
    This data is cached from the Redis alpha stream.
    """
    data = feature_cache.get_all()
    return success_response(data=data)

@router.get("/features/{symbol}")
async def get_symbol_features(symbol: str):
    """
    Returns the latest technical features for a specific symbol.
    """
    data = feature_cache.get_for_symbol(symbol)
    if not data:
        return success_response(data={})
    return success_response(data=data)
