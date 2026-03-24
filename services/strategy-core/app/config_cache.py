
import json
import os
import redis
from typing import Optional, Dict
from app.utils.redis_client import get_redis_client

class RedisConfigCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConfigCache, cls).__new__(cls)
            cls._instance.client = get_redis_client()
            cls._instance.local_cache = {} # id -> config
        return cls._instance

    def get_config(self, strategy_id: str) -> Optional[dict]:
        # Try local cache first
        if strategy_id in self.local_cache:
            return self.local_cache[strategy_id]
        
        # Try Redis
        config_str = self.client.get(f"strategy:config:{strategy_id}")
        if config_str:
            config = json.loads(config_str)
            self.local_cache[strategy_id] = config
            return config
            
        return None

    def set_config(self, strategy_id: str, config: dict):
        self.local_cache[strategy_id] = config
        self.client.set(f"strategy:config:{strategy_id}", json.dumps(config))
        # Publish update event
        self.client.publish("system:config:update", strategy_id)

    def invalidate(self, strategy_id: str):
        if strategy_id in self.local_cache:
            del self.local_cache[strategy_id]
        # Redis logic if needed

config_cache = RedisConfigCache()
