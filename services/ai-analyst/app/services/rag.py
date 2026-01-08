from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.services.gemini import GeminiClient
import uuid
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, gemini_client: GeminiClient = None):
        self.qdrant = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=settings.QDRANT_GRPC_HTTPS
        )
        self.gemini = gemini_client or GeminiClient()
        self.journal_collection = "journal_entries"
        self.strategy_collection = "strategies"
        self.docs_collection = "system_docs"
        
        self._ensure_collection(self.journal_collection)
        self._ensure_collection(self.strategy_collection)
        self._ensure_collection(self.docs_collection)

    def _ensure_collection(self, name: str):
        """Ensure the Qdrant collection exists with proper config."""
        try:
            self.qdrant.get_collection(name)
        except Exception:
            logger.info(f"Creating collection {name}")
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=768,  # Gemini 1.5 embedding dimension
                    distance=models.Distance.COSINE
                )
            )

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Gemini API."""
        try:
            result = await self.gemini.client.aio.models.embed_content(
                model="models/text-embedding-004",
                contents=text
            )
            return result.embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def ingest_journal_entry(self, entry_id: str, content: str, user_id: str, metadata: dict = None):
        """Embed and upsert a journal entry."""
        embedding = await self._get_embedding(content)
        
        point = models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(entry_id))),
            vector=embedding,
            payload={
                "content": content,
                "original_id": entry_id,
                "user_id": user_id,
                **(metadata or {})
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.journal_collection,
            points=[point]
        )
        logger.info(f"Ingested journal entry {entry_id} for user {user_id}")

    async def ingest_strategy(self, strategy_id: str, code: str, user_id: str, stats: dict = None):
        """Embed and upsert a strategy code snippet with performance stats."""
        # Create a rich textual representation for embedding
        text_rep = f"Strategy Code:\n{code}\n\nPerformance:\n{stats}"
        embedding = await self._get_embedding(text_rep)
        
        point = models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(strategy_id))),
            vector=embedding,
            payload={
                "code": code,
                "stats": stats or {},
                "original_id": strategy_id,
                "user_id": user_id
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.strategy_collection,
            points=[point]
        )
        logger.info(f"Ingested strategy {strategy_id} for user {user_id}")

    async def search_similar_entries(self, query: str, user_id: str, limit: int = 3) -> list[str]:
        """Search for semantically similar journal entries for a specific user."""
        embedding = await self._get_embedding(query)
        
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
        )

        search_result = self.qdrant.search(
            collection_name=self.journal_collection,
            query_vector=embedding,
            query_filter=search_filter,
            limit=limit
        )
        
        return [hit.payload["content"] for hit in search_result]

    async def search_similar_strategies(self, query: str, user_id: str, limit: int = 3) -> list[dict]:
        """Search for similar strategies to help with coding/optimization."""
        embedding = await self._get_embedding(query)
        
        # Optional: Allow searching "Global Wisdom" (no user_id filter) or just "My Strategies"
        # For now, let's search strict user_id to respect privacy/isolation
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
        )

        search_result = self.qdrant.search(
            collection_name=self.strategy_collection,
            query_vector=embedding,
            query_filter=search_filter,
            limit=limit
        )
        
        results = []
        for hit in search_result:
            results.append({
                "code": hit.payload.get("code"),
                "stats": hit.payload.get("stats"),
                "score": hit.score
            })
        return results

    async def ingest_document(self, filename: str, content: str, doc_type: str = "spec"):
        """Ingest a system documentation file (Spec or Guide)."""
        embedding = await self._get_embedding(content)
        
        point = models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, filename)),
            vector=embedding,
            payload={
                "filename": filename,
                "content": content,
                "doc_type": doc_type
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.docs_collection,
            points=[point]
        )
        logger.info(f"Ingested document: {filename}")

    async def search_documentation(self, query: str, limit: int = 3) -> list[dict]:
        """Search system documentation for context."""
        embedding = await self._get_embedding(query)
        
        search_result = self.qdrant.search(
            collection_name=self.docs_collection,
            query_vector=embedding,
            limit=limit
        )
        
        return [{
            "filename": hit.payload["filename"],
            "content": hit.payload["content"],
            "score": hit.score
        } for hit in search_result]
