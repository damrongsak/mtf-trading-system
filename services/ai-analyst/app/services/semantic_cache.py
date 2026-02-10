
import logging
from typing import Optional, List
import numpy as np
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

from app.core.config import settings
from app.services.gemini import GeminiClient

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
                ]
            })
            
            # Connect to Redis
            self.index = SearchIndex(schema, redis_url=settings.redis.url)
            self.index.create(overwrite=False)
            logger.info("Semantic Cache index initialized.")
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
                 return_fields=["response", "original_query", "vector_distance"],
                 num_results=1
            )
            
            results = self.index.query(query_vector)
            
            if results and len(results) > 0:
                 best_match = results[0]
                 # Cosine distance: 0 is identical, 1 is orthogonal.
                 # Similarity = 1 - Distance
                 dist = float(best_match.get('vector_distance', 1.0))
                 similarity = 1 - dist
                 
                 logger.debug(f"Cache Match: {similarity:.4f} (Threshold: {threshold})")
                 
                 if similarity >= threshold:
                     logger.info(f"Semantic Cache HIT! (Sim: {similarity:.4f})")
                     return best_match.get("response")
                     
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
                "response": response
            }]
            
            self.index.load(data)
            logger.debug(f"Cached query: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"Cache store failed: {e}")
