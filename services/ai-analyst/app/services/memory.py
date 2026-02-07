from app.services.rag import RAGService
import logging

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Manages Long-Term Memory (User Facts) for the AI Analyst.
    Backed by Qdrant 'user_memory' collection.
    """
    def __init__(self, rag_service: RAGService):
        self.rag = rag_service

    async def add_user_fact(self, user_id: str, fact: str):
        """
        Stores a specific fact or preference about the user.
        Example: "User prefers Delta Neutral strategies"
        """
        try:
            # We reuse the RAG service's upsert logic but targeting the user_memory collection
            # Note: We need to extend RAGService to support this specific method to keep it clean,
            # or use a generic 'ingest_text' method. For now, we will add a dedicated method to RAGService.
            await self.rag.add_user_memory(user_id, fact)
            logger.info(f"Learned new fact for user {user_id}: {fact[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save user fact: {e}")

    async def get_user_context(self, user_id: str, query: str = "", limit: int = 5) -> str:
        """
        Retrieves relevant user facts for the current session context.
        If query is empty, might return most recent or 'pinned' facts (future feature).
        For now, it uses the current query to find relevant past preferences.
        """
        try:
            facts = await self.rag.search_user_memory(user_id, query, limit)
            if not facts:
                return "No specific user preferences found."
            
            bullet_points = "\n- ".join(facts)
            return f"User Preferences / Facts:\n- {bullet_points}"
        except Exception as e:
            logger.error(f"Failed to retrieve user context: {e}")
            return ""
