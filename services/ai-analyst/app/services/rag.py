from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.services.gemini import GeminiClient
import uuid
import logging



logger = logging.getLogger(__name__)

class SimpleTextSplitter:
    """A zero-dependency text splitter that chunks by character count with overlap."""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: list = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> list[str]:
        """Iteratively splits text trying to keep semantic blocks together."""
        final_chunks = []
        
        # Simple loop for now: explicit slicing with overlap
        # A full recursive splitter is complex; this is a robust "Good Enough" fallback
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            
            # If we are not at the end of text, try to find a separator to break cleanly
            if end < text_len:
                # Search backwards from 'end' for the best separator
                found_cut = False
                for sep in self.separators:
                    cut_idx = text.rfind(sep, start, end)
                    if cut_idx != -1 and cut_idx > start + (self.chunk_size // 2): 
                        # Only accept cut if it's materially advanced
                        end = cut_idx + len(sep)
                        found_cut = True
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                final_chunks.append(chunk)
            
            # Move start forward, accounting for overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop if overlap >= advance
            if start >= end:
                start = end  # Force advance if we are stuck

        return final_chunks

class RAGService:
    def __init__(self, gemini_client: GeminiClient = None):
        import warnings
        with warnings.catch_warnings():
            # Suppress "Api key is used with an insecure connection" warning for interior Docker network
            warnings.filterwarnings("ignore", message=".*Api key is used with an insecure connection.*")
            self.qdrant = QdrantClient(
                host=settings.qdrant.host,
                port=settings.qdrant.port,
                api_key=settings.qdrant.api_key,
                https=settings.qdrant.grpc_https,
                timeout=5.0
            )
        self.gemini = gemini_client or GeminiClient()
        self.journal_collection = "journal_entries"
        self.strategy_collection = "strategies"
        self.docs_collection = "system_docs"
        self.user_memory = "user_memory"
        
        try:
            self._ensure_collection(self.journal_collection)
            self._ensure_collection(self.strategy_collection)
            self._ensure_collection(self.docs_collection)
            self._ensure_collection(self.user_memory)
        except Exception as e:
            logger.warning(f"Could not ensure collections on init (Qdrant offline?): {e}")

    def _ensure_collection(self, name: str):
        """Ensure the Qdrant collection exists with proper config."""
        try:
            self.qdrant.get_collection(name)
        except Exception:
            logger.info(f"Creating collection {name}")
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=3072,  # Gemini-embedding-001 dimension
                    distance=models.Distance.COSINE
                )
            )

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Gemini API."""
        try:
            result = await self.gemini.client.aio.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text
            )
            # Handle new SDK response structure
            if hasattr(result, 'embeddings') and result.embeddings:
                return result.embeddings[0].values
            elif hasattr(result, 'embedding'):
                 return result.embedding
            else:
                 # Fallback/Debug
                 logger.error(f"Unknown embedding response structure: {dir(result)}")
                 raise ValueError("Could not extract embedding from response")
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

        search_result = self.qdrant.query_points(
            collection_name=self.journal_collection,
            query=embedding,
            query_filter=search_filter,
            limit=limit
        ).points
        
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

        search_result = self.qdrant.query_points(
            collection_name=self.strategy_collection,
            query=embedding,
            query_filter=search_filter,
            limit=limit
        ).points
        
        results = []
        for hit in search_result:
            results.append({
                "code": hit.payload.get("code"),
                "stats": hit.payload.get("stats"),
                "score": hit.score
            })
        return results



    async def ingest_document(self, filename: str, content: str, doc_type: str = "spec"):
        """Ingest a system documentation file (Spec or Guide) with chunking."""
        import asyncio

        splitter = SimpleTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(content)
        
        points = []
        
        # Limit concurrency to avoid rate limits
        sem = asyncio.Semaphore(5)

        async def process_chunk(i, chunk_text):
            async with sem:
                try:
                    embedding = await self._get_embedding(chunk_text)
                    
                    # Create a deterministic ID based on filename + chunk index
                    chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}_chunk_{i}"))
                    
                    return models.PointStruct(
                        id=chunk_id,
                        vector=embedding,
                        payload={
                            "filename": filename,
                            "content": chunk_text,
                            "doc_type": doc_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                    return None

        tasks = [process_chunk(i, c) for i, c in enumerate(chunks)]
        results = await asyncio.gather(*tasks)
        
        points = [p for p in results if p is not None]
        
        # Upsert in batch
        if points:
            # Batch upsert to Qdrant (chunks of 100 to be safe)
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                try:
                    self.qdrant.upsert(
                        collection_name=self.docs_collection,
                        points=batch
                    )
                except Exception as e:
                    logger.error(f"Failed to upsert batch {i}: {e}")

            logger.info(f"Ingested document: {filename} ({len(points)} chunks)")
        else:
            logger.warning(f"No chunks created for {filename}")

    async def search_documentation(self, query: str, limit: int = 3) -> list[dict]:
        """Search system documentation for context."""
        embedding = await self._get_embedding(query)
        
        search_result = self.qdrant.query_points(
            collection_name=self.docs_collection,
            query=embedding,
            limit=limit
        ).points
        
        return [{
            "filename": hit.payload["filename"],
            "content": hit.payload["content"],
            "score": hit.score
        } for hit in search_result]

    async def search_user_memory(self, user_id: str, query: str, limit: int = 5) -> list[str]:
        """Search long-term user memory."""
        embedding = await self._get_embedding(query)
        
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
        )

        try:
            search_result = self.qdrant.query_points(
                collection_name=self.user_memory,
                query=embedding,
                query_filter=search_filter,
                limit=limit
            ).points
            
            return [hit.payload["content"] for hit in search_result]
        except Exception:
            # Collection might not exist yet or empty
            return []

    async def add_user_memory(self, user_id: str, content: str):
        """Store a user fact."""
        embedding = await self._get_embedding(content)
        
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": content,
                "user_id": user_id,
                "timestamp": uuid.uuid1().time  # roughly timestamp
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.user_memory,
            points=[point]
        )
