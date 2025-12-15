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
        self.collection_name = "journal_entries"
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the Qdrant collection exists with proper config."""
        try:
            self.qdrant.get_collection(self.collection_name)
        except Exception:
            logger.info(f"Creating collection {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=768,  # Gemini 1.5 embedding dimension
                    distance=models.Distance.COSINE
                )
            )

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Gemini API."""
        # Note: GeminiClient needs an embedding method. Adding a loose wrapper here 
        # or assuming GeminiClient has it. Let's use the raw client for now if not exposed.
        try:
            result = await self.gemini.client.aio.models.embed_content(
                model="models/text-embedding-004",
                contents=text
            )
            return result.embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def ingest_journal_entry(self, entry_id: str, content: str, metadata: dict = None):
        """Embed and upsert a journal entry."""
        embedding = await self._get_embedding(content)
        
        point = models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(entry_id))), # Ensure valid UUID
            vector=embedding,
            payload={
                "content": content,
                "original_id": entry_id,
                **(metadata or {})
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        logger.info(f"Ingested journal entry {entry_id}")

    async def search_similar_entries(self, query: str, limit: int = 3) -> list[str]:
        """Search for semantically similar journal entries."""
        embedding = await self._get_embedding(query)
        
        search_result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit
        )
        
        return [hit.payload["content"] for hit in search_result]
