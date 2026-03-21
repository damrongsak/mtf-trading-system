import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
import uuid
from datetime import datetime, timezone

from app.models.memory import EpisodicMemory
from app.services.gemini import GeminiClient

logger = logging.getLogger("ai-analyst")

class EpisodicMemoryService:
    """
    Manages Episodic Memory (Experience) for the AI Analyst using pgvector.
    Provides semantic retrieval with strict RBAC enforcement (User/Fund).
    """
    def __init__(self, db: Session, gemini_client: GeminiClient = None):
        self.db = db
        self.gemini = gemini_client or GeminiClient()
        self.model_id = "models/gemini-embedding-001"

    async def _get_embedding(self, text_content: str) -> List[float]:
        """Generate embedding using Gemini API."""
        try:
            result = await self.gemini.client.aio.models.embed_content(
                model=self.model_id,
                contents=text_content
            )
            if hasattr(result, 'embeddings') and result.embeddings:
                return result.embeddings[0].values
            elif hasattr(result, 'embedding'):
                 return result.embedding
            else:
                 raise ValueError("Could not extract embedding from response")
        except Exception as e:
            logger.error(f"Memory Embedding failed: {e}")
            raise

    async def add_memory(
        self, 
        user_id: uuid.UUID, 
        content: str, 
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        intent: Optional[str] = None,
        fund_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EpisodicMemory:
        """
        Stores a new episodic memory (Lesson Learned).
        """
        embedding = await self._get_embedding(content)
        
        memory = EpisodicMemory(
            user_id=user_id,
            fund_id=fund_id,
            symbol=symbol,
            timeframe=timeframe,
            intent=intent,
            content=content,
            embedding=embedding,
            meta=metadata or {}
        )
        
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.info(f"Saved episodic memory {memory.id} for user {user_id} (Symbol: {symbol})")
        return memory

    async def retrieve_relevant_memories(
        self, 
        user_id: uuid.UUID, 
        query: str, 
        symbol: Optional[str] = None,
        fund_id: Optional[uuid.UUID] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic retrieval of memories using cosine similarity.
        Strict isolation by user_id OR shared fund_id.
        """
        query_embedding = await self._get_embedding(query)
        
        # pgvector uses <=> for cosine distance (smaller is more similar)
        # We need to cast query_embedding to a string format [1.2, 3.4, ...] for pgvector
        # Or use the specific ARRAY cast.
        
        # RBAC Filter: (user_id == target) OR (fund_id == target_fund AND fund_id IS NOT NULL)
        conditions = [EpisodicMemory.user_id == user_id]
        if fund_id:
            conditions.append(EpisodicMemory.fund_id == fund_id)
        
        # Optional: Boost specific symbol matches
        
        query_stmt = (
            self.db.query(EpisodicMemory)
            .filter(or_(*conditions))
            .order_by(EpisodicMemory.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        results = query_stmt.all()
        
        return [
            {
                "id": str(m.id),
                "content": m.content,
                "symbol": m.symbol,
                "intent": m.intent,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "distance": 0.0 # Distance calculation if needed
            }
            for m in results
        ]
