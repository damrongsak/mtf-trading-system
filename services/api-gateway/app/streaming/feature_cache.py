import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FeatureCache:
    """
    Singleton cache to store the latest features for each symbol.
    Acts as a Read Model for the Feature Matrix UI.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeatureCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        # symbol -> feature_dict
        self._cache: Dict[str, Any] = {}
        self.initialized = True

    def update(self, symbol: str, features: Dict[str, Any]):
        """Update the cache with new features for a symbol."""
        self._cache[symbol] = features
        logger.debug(f"Updated FeatureCache for {symbol}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all cached features as a list."""
        return list(self._cache.values())

    def get_for_symbol(self, symbol: str) -> Any:
        """Return features for a specific symbol."""
        return self._cache.get(symbol)

    def clear(self):
        """Clear the cache."""
        self._cache.clear()

feature_cache = FeatureCache()
