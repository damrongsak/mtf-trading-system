import logging
import json
import time
from typing import Any, Optional, Dict, List
import redis.asyncio as aioredis
import os
import httpx

logger = logging.getLogger(__name__)

class ExecutionCache:
    """
    Tiered Cache for Execution Service:
    - L1: In-memory dictionary (TTL-based)
    - L2: Redis Hash/String
    - L3: PostgreSQL (Fallback)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutionCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self._l1_cache: Dict[str, Dict[str, Any]] = {}  # key -> {"data": data, "expiry": ts}
        self.default_ttl = 86400  # 24 hours (HFT-lite hot-path protection)
        self.initialized = True

    async def _get_redis(self):
        if not self.redis:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self.redis

    def _get_l1(self, key: str) -> Optional[Any]:
        if key in self._l1_cache:
            item = self._l1_cache[key]
            if time.time() < item["expiry"]:
                return item["data"]
            else:
                del self._l1_cache[key]
        return None

    def _set_l1(self, key: str, data: Any, ttl: int = None):
        expiry = time.time() + (ttl or self.default_ttl)
        self._l1_cache[key] = {"data": data, "expiry": expiry}

    async def get_account(self, account_id: str) -> Optional[Dict]:
        key = f"exec:account:{account_id}"
        
        # Check L1
        cached = self._get_l1(key)
        if cached:
            return cached
        
        # Check L2 (Redis)
        try:
            r = await self._get_redis()
            data_json = await r.get(key)
            if data_json:
                data = json.loads(data_json)
                self._set_l1(key, data)
                return data
        except Exception as e:
            logger.error(f"Redis Cache Error (get_account): {e}")
            
        return None

    async def set_account(self, account_id: str, data: Dict, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        key = f"exec:account:{account_id}"
        self._set_l1(key, data, ttl)
        try:
            r = await self._get_redis()
            res = await r.set(key, json.dumps(data), ex=ttl)
            logger.info(f"DEBUG: Redis SET {key} (ttl={ttl}) result: {res}")
        except Exception as e:
            logger.error(f"Redis Cache Error (set_account): {e}")

    async def get_fund(self, fund_id: str) -> Optional[Dict]:
        key = f"exec:fund:{fund_id}"
        cached = self._get_l1(key)
        if cached:
            return cached
            
        try:
            r = await self._get_redis()
            data_json = await r.get(key)
            if data_json:
                data = json.loads(data_json)
                self._set_l1(key, data)
                return data
        except Exception as e:
            logger.error(f"Redis Cache Error (get_fund): {e}")
        return None

    async def set_fund(self, fund_id: str, data: Dict, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        key = f"exec:fund:{fund_id}"
        self._set_l1(key, data, ttl)
        try:
            r = await self._get_redis()
            await r.set(key, json.dumps(data), ex=ttl)
        except Exception as e:
            logger.error(f"Redis Cache Error (set_fund): {e}")

    async def get_credentials(self, account_id: str) -> Optional[Dict]:
        """Returns decrypted credentials from memory cache."""
        key = f"exec:creds:{account_id}"
        return self._get_l1(key)

    async def set_credentials(self, account_id: str, creds: Dict, ttl: int = 3600):
        """Caches decrypted credentials in L1 (memory) and persists cTrader mapping in Redis."""
        key = f"exec:creds:{account_id}"
        self._set_l1(key, creds, ttl)
        
        # Also store cTrader account ID mapping if this is a cTrader account
        if creds and "account_id" in creds:
             ctid_key = f"exec:ctid:{creds['account_id']}"
             self._set_l1(ctid_key, account_id, ttl)  # L1 for fast local read
             
             # Also store in Redis for cross-process access (e.g. Worker)
             try:
                 r = await self._get_redis()
                 await r.set(ctid_key, account_id, ex=ttl)
             except Exception as e:
                 logger.error(f"Failed to persist ctid mapping in Redis: {e}")

    async def get_broker_account_id_by_ctid(self, ctid_account_id: str) -> Optional[str]:
        """Get broker_account_id (UUID) from cTrader account ID."""
        key = f"exec:ctid:{ctid_account_id}"
        cached = self._get_l1(key)
        if cached:
            return cached
            
        try:
            r = await self._get_redis()
            data = await r.get(key)
            if data:
                self._set_l1(key, data)
                return data
        except Exception as e:
            logger.error(f"Redis Cache Error (get_broker_account_id_by_ctid): {e}")
        return None

    async def get_risk_filters(self, fund_id: str, account_id: str = None) -> Optional[List[Dict]]:
        key = f"exec:filters:{fund_id}:{account_id or 'none'}"
        cached = self._get_l1(key)
        if cached:
            return cached
            
        try:
            r = await self._get_redis()
            data_json = await r.get(key)
            if data_json:
                data = json.loads(data_json)
                self._set_l1(key, data, ttl=3600) # Hot data, increased TTL
                return data
        except Exception as e:
            logger.error(f"Redis Cache Error (get_risk_filters): {e}")
        return None

    async def set_risk_filters(self, fund_id: str, filters: List[Dict], account_id: str = None, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl  # Default to 24h as per HFT-lite standards
        key = f"exec:filters:{fund_id}:{account_id or 'none'}"
        self._set_l1(key, filters, ttl=ttl)
        try:
            r = await self._get_redis()
            await r.set(key, json.dumps(filters), ex=ttl)
        except Exception as e:
            logger.error(f"Redis Cache Error (set_risk_filters): {e}")

    def invalidate(self, key: str):
        if key in self._l1_cache:
            del self._l1_cache[key]
        # Redis invalidation usually handled by publishers or TTL

    async def get_symbols(self, provider: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch symbols from L1 cache, or Redis (ECST), or fallback to API Gateway.
        """
        key = f"exec:symbols:{provider}"
        cached = self._get_l1(key)
        if cached:
            return cached
            
        try:
            r = await self._get_redis()
            data_json = await r.get(key)
            if data_json:
                data = json.loads(data_json)
                self._set_l1(key, data, ttl=300)
                return data
        except Exception as e:
            logger.error(f"Redis Cache Error (get_symbols) for {provider}: {e}")
            
        # Fallback to Data Pipeline if not in Redis
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"ECST Symbol Cache miss for {provider} (Attempt {attempt+1}/{max_retries}), fetching via HTTP fallback...")
                # Use Data Pipeline directly to avoid circular dependency with API Gateway
                api_url = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
                
                # Use httpx client (create minimal wrapper)
                async with httpx.AsyncClient() as client:
                    # Direct call to data-pipeline /api/v1/symbols
                    resp = await client.get(f"{api_url}/api/v1/symbols", params={"broker": provider}, timeout=15.0)
                    
                    if resp.status_code == 200:
                        raw_data = resp.json()
                        # The Data Pipeline returns List[dict] directly
                        if isinstance(raw_data, list):
                            data = raw_data
                        elif isinstance(raw_data, dict) and "data" in raw_data:
                            data = raw_data["data"]
                        else:
                            data = raw_data
                            
                        # data is assumed to be List[Dict] matching MarketSymbol DB schema
                        # Store in Redis and L1
                        self._set_l1(key, data, ttl=300)
                        try:
                            r = await self._get_redis()
                            await r.set(key, json.dumps(data), ex=300)
                        except Exception:
                            pass
                        return data
                    else:
                        logger.error(f"HTTP fallback get_symbols failed: {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"HTTP fallback get_symbols Exception (Attempt {attempt+1}): {repr(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying symbol hydration in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            
        return None

    async def set_order_context(self, broker_order_id: str, context: Dict, expire: int = 3600):
        """[HFT-lite] Store trade context for async fill enrichment."""
        key = f"exec:order_ctx:{broker_order_id}"
        try:
            r = await self._get_redis()
            await r.set(key, json.dumps(context), ex=expire)
        except Exception as e:
            logger.error(f"Redis Cache Error (set_order_context): {e}")

    async def get_order_context(self, broker_order_id: str) -> Optional[Dict]:
        """[HFT-lite] Retrieve trade context for async fill enrichment."""
        key = f"exec:order_ctx:{broker_order_id}"
        try:
            r = await self._get_redis()
            data_json = await r.get(key)
            if data_json:
                return json.loads(data_json)
        except Exception as e:
            logger.error(f"Redis Cache Error (get_order_context): {e}")
        return None

    async def delete_order_context(self, broker_order_id: str):
        """[HFT-lite] Cleanup order context after fill processing."""
        key = f"exec:order_ctx:{broker_order_id}"
        try:
            r = await self._get_redis()
            await r.delete(key)
        except Exception as e:
            logger.error(f"Redis Cache Error (delete_order_context): {e}")

execution_cache = ExecutionCache()
