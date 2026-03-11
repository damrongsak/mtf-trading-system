
import logging
from typing import Optional, List
import numpy as np
import time
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

from app.core.config import settings
from app.services.gemini import GeminiClient

from app.core.globals import services

logger = logging.getLogger(__name__)

class SemanticCache:
    def __init__(self, gemini_client: GeminiClient = None):
        self.gemini = gemini_client or GeminiClient()
        self.index_name = "semantic_cache"
        self.index = None
        self._init_index()

    def _init_index(self):
        # RedisVL Schema Definition
        try:
            schema = IndexSchema.from_dict({
                "index": {
                    "name": self.index_name,
                    "prefix": "cache",
                    "storage_type": "hash",
                },
                "fields": [
                    {"name": "original_query", "type": "text"},
                    {
                        "name": "vector", 
                        "type": "vector", 
                        "attrs": {
                            "dims": settings.gemini.embedding_dim, 
                            "distance_metric": "cosine", 
                            "algorithm": "flat",
                            "datatype": "float32"
                        }
                    },
                    {"name": "response", "type": "text"},
                    {"name": "timestamp", "type": "numeric"},
                ]
            })
            
            # Connect to Redis
            self.index = SearchIndex(schema, redis_url=settings.redis.url)
            # overwrite=True once to apply schema change if needed, 
            # but for safety in production usually we'd check if field exists.
            # Here, we'll use overwrite=True if the index already exists but with old schema.
            # Simple approach: create handles it if overwrite=False, but it won't add fields to existing.
            # We'll drop and recreate since it's just a cache.
            if self.index.exists():
                logger.info("Dropping existing semantic_cache index for schema update...")
                self.index.delete()
            
            self.index.create(overwrite=True)
            logger.info("Semantic Cache index initialized with TTL support.")
        except Exception as e:
             logger.warning(f"Failed to init Semantic Cache index: {e}")

    async def _get_embedding(self, text: str) -> List[float]:
        try:
             # Use the same model as RAGService
             res = await self.gemini.client.aio.models.embed_content(
                 model="models/gemini-embedding-001",
                 contents=text
             )
             if hasattr(res, 'embeddings') and res.embeddings:
                 return res.embeddings[0].values
             elif hasattr(res, 'embedding'):
                 return res.embedding
             else:
                 return []
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    async def check(self, query: str, threshold: float = 0.9) -> Optional[str]:
        """Check cache for semantically similar query."""
        if not self.index:
            return None
            
        try:
            vector = await self._get_embedding(query)
            if not vector:
                return None
                
            query_vector = VectorQuery(
                 vector=vector,
                 vector_field_name="vector",
                 return_fields=["response", "original_query", "vector_distance", "timestamp"],
                 num_results=1
            )
            
            results = self.index.query(query_vector)
            
            redis = services.get("redis")
            if results and len(results) > 0:
                 best_match = results[0]
                 # Cosine distance: 0 is identical, 1 is orthogonal.
                 # Similarity = 1 - Distance
                 dist = float(best_match.get('vector_distance', 1.0))
                 similarity = 1 - dist
                 
                 logger.debug(f"Cache Match: {similarity:.4f} (Threshold: {threshold})")
                 
                 if similarity >= threshold:
                     # Check freshness
                     cached_ts = float(best_match.get("timestamp", 0))
                     age_seconds = time.time() - cached_ts
                     # For market data, we want 1 hour (3600s) max age
                     if age_seconds <= 3600:
                         logger.info(f"Semantic Cache HIT! (Sim: {similarity:.4f}, Age: {age_seconds:.0f}s)")
                         if redis:
                             await redis.incr("stats:cache:hit")
                         return best_match.get("response")
                     else:
                         logger.info(f"Semantic Cache STALE! (Age: {age_seconds:.0f}s > 3600s)")
            
            if redis:
                await redis.incr("stats:cache:miss")
            return None
            
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            return None

    async def store(self, query: str, response: str):
        """Store query and response in cache."""
        if not self.index:
            return

        try:
            vector = await self._get_embedding(query)
            if not vector:
                return

            # Store in Redis via RedisVL
            # Must convert to bytes for Redis Hash storage
            vector_bytes = np.array(vector, dtype=np.float32).tobytes()
            
            data = [{
                "original_query": query,
                "vector": vector_bytes,
                "response": response,
                "timestamp": time.time()
            }]
            
            self.index.load(data)
            logger.debug(f"Cached query: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"Cache store failed: {e}")
