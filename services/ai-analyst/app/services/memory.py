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

    async def get_adaptive_context(self, user_id: str, query: str = "", limit: int = 3) -> str:
        """
        Hybrid Memory Injection (Approved v2.6).
        Combines User Preferences + Historical Lessons Learned (RAG).
        """
        context_parts = []
        
        # 1. User Facts
        facts = await self.get_user_context(user_id, query, limit=limit)
        if facts:
            context_parts.append(facts)
            
        # 2. Historical Lessons (Post-Mortem Wisdom)
        try:
            lessons = await self.rag.search_lessons(query, user_id, limit=limit)
            if lessons:
                lessons_str = "\n- ".join(lessons)
                context_parts.append(f"Institutional Wisdom (Past Lessons):\n- {lessons_str}")
        except Exception as e:
            logger.error(f"Adaptive context search failed: {e}")
            
        return "\n\n".join(context_parts)

    async def save_persistent_skill(self, user_id: str, name: str, code: str):
        """
        Persistent Skills (OpenClaw Style).
        Saves a successful Python script for future O(1) reuse.
        """
        import os
        base_dir = "/app/persistent_skills"
        os.makedirs(base_dir, exist_ok=True)
        
        file_path = os.path.join(base_dir, f"{name}.py")
        try:
            with open(file_path, "w") as f:
                f.write(f"# Persistent Skill: {name}\n# User: {user_id}\n\n{code}")
            
            # Also register in RAG so the agent can find it via keyword search
            await self.rag.ingest_document(
                filename=f"skill_{name}.py",
                content=f"Persistent Skill: {name}\n\n{code}",
                doc_type="skill"
            )
            logger.info(f"Persistent skill '{name}' saved for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save persistent skill: {e}")
