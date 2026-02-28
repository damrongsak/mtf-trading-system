from qdrant_client import QdrantClient, models
from app.core.config import settings
from app.services.gemini import GeminiClient
import os
import json
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import time
import re
from sqlalchemy.orm import Session
from app.models.rag import LibraryBook, IngestionStatus
from app.database import SessionLocal

logger = logging.getLogger(__name__)

class QuantMarkdownSplitter:
    """
    Advanced Splitter for Quant books
    - Splits by Markdown Headers (##, ###)
    - Preserves Code Blocks within the same chunk if possible
    - Cleans PDF artifacts (Page numbers, extra spaces, etc.)
    """
    def __init__(self, max_chunk_size: int = 3000, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """Clean noise artifacts from PDF-to-Markdown conversion."""
        # 1. Remove Form Feed characters (common in PDF conversions)
        text = text.replace('\x0c', '')
        
        # 2. Remove Page numbers (e.g., "Page 12", or standalone numbers on new lines)
        text = re.sub(r'(?i)^\s*page\s+\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # 3. Handle excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def split_text(self, text: str) -> list[str]:
        text = self.clean_text(text)
        chunks = []
        
        # Split by Markdown Headers (Level 2 and 3)
        # Using lookahead to keep the headers in the resulting sections
        sections = re.split(r'(?=\n#{2,3}\s)', text)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # If a section is too large, split it further by paragraphs
            if len(section) > self.max_chunk_size:
                sub_sections = self._split_large_section(section)
                chunks.extend(sub_sections)
            else:
                chunks.append(section)
                
        return chunks

    def _split_large_section(self, section: str) -> list[str]:
        """Split a large section into smaller chunks while trying to preserve paragraphs."""
        chunks = []
        paragraphs = section.split('\n\n')
        current_chunk = ""
        
        for p in paragraphs:
            if len(p) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split huge paragraphs by line if necessary
                lines = p.split('\n')
                line_chunk = ""
                for line in lines:
                    if len(line_chunk) + len(line) + 1 < self.max_chunk_size:
                        line_chunk += line + "\n"
                    else:
                        if line_chunk: chunks.append(line_chunk.strip())
                        line_chunk = line + "\n"
                if line_chunk: chunks.append(line_chunk.strip())
                continue

            if len(current_chunk) + len(p) + 2 < self.max_chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

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
        self.library_collection = "quant_library"
        
        try:
            self._ensure_collection(self.journal_collection)
            self._ensure_collection(self.strategy_collection)
            self._ensure_collection(self.docs_collection)
            self._ensure_collection(self.user_memory)
            self._ensure_collection(self.library_collection)
        except Exception as e:
            logger.warning(f"Could not ensure collections on init (Qdrant offline?): {e}")

    def get_collection_stats(self, name: str) -> dict:
        """Get collection telemetry."""
        try:
            collection_info = self.qdrant.get_collection(collection_name=name)
            return {
                "status": collection_info.status.value,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value
                }
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {name}: {e}")
            return {"error": str(e)}

    def clear_collection(self, name: str):
        """Wipe all points from a collection."""
        try:
            self.qdrant.delete_collection(collection_name=name)
            self._ensure_collection(name)
            logger.info(f"Cleared collection: {name}")
        except Exception as e:
            logger.error(f"Failed to clear collection {name}: {e}")
            raise

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

    async def search_library(self, query: str, limit: int = 5, filters: dict = None, expand_context: bool = True) -> list[dict]:
        """
        Search the quantitative finance library for insights.
        - Supports metadata filtering.
        - Optionally expands context by retrieving adjacent chunks.
        - Includes structured logging for observability.
        """
        start_time = time.time()
        
        logger.info(f"RAG Search: query='{query}' filters={filters} limit={limit}")
        
        embedding = await self._get_embedding(query)
        
        # Build Qdrant filter
        qdrant_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            qdrant_filter = models.Filter(must=must_conditions)

        search_result = self.qdrant.query_points(
            collection_name=self.library_collection,
            query=embedding,
            query_filter=qdrant_filter,
            limit=limit * 2 # Fetch more for hybrid boost and reranking
        ).points
        
        results = []
        source_files = set()
        
        for hit in search_result:
            file_name = hit.payload.get("filename")
            chunk_idx = hit.payload.get("chunk_index")
            content = hit.payload.get("content")
            
            if file_name:
                source_files.add(file_name)
            
            # Hybrid Score (Keyword Boost)
            keyword_score = self._calculate_keyword_score(query, content)
            combined_score = (hit.score * 0.7) + (keyword_score * 0.3)

            if expand_context and file_name and chunk_idx is not None:
                content = await self._expand_context(file_name, chunk_idx, content)

            results.append({
                "filename": file_name,
                "content": content,
                "score": combined_score,
                "original_vector_score": hit.score,
                "keyword_score": keyword_score,
                "metadata": {
                    "chunk_index": chunk_idx,
                    "total_chunks": hit.payload.get("total_chunks"),
                    **{k: v for k, v in hit.payload.items() if k not in ["content", "filename", "chunk_index", "total_chunks"]}
                }
            })
        
        # Sort by hybrid score before reranking
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]

        duration = time.time() - start_time
        logger.info(f"RAG Search Complete: results={len(results)} sources={source_files} time={duration:.3f}s")
        
        # Phase 3: Cross-Encoder Reranking (Gemini)
        if results and len(results) > 1:
            results = await self._rerank_with_gemini(query, results)
            logger.info(f"RAG Reranking Complete: top_score={results[0]['score'] if results else 0:.4f}")

        return results

    def _calculate_keyword_score(self, query: str, content: str) -> float:
        """Simple keyword overlap score (Hybrid Search lite)."""
        words = re.findall(r'\w+', query.lower())
        if not words: return 0.0
        
        content_lower = content.lower()
        matches = sum(1 for word in words if word in content_lower)
        return matches / len(words)

    async def _rerank_with_gemini(self, query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
        """Use Gemini as a Cross-Encoder to re-rank the top candidates."""
        if not candidates:
            return []
            
        # Prepare ranking prompt
        context_items = []
        for i, c in enumerate(candidates):
            # Use only a snippet for ranking to save tokens
            snippet = c['content'][:1000]
            context_items.append(f"ID: {i}\nContent: {snippet}\n---")
            
        items_str = "\n".join(context_items)
        prompt = f"""
        You are an expert quantitative researcher. Rank the following context snippets by their relevance to the user's query.
        
        User Query: "{query}"
        
        Context Snippets:
        {items_str}
        
        Task: 
        1. Evaluate each snippet for its technical accuracy and relevance to the query.
        2. Identify the top {top_n} most relevant snippets.
        3. Return your response as a JSON list of indices in order of relevance (most relevant first).
        
        Format: [2, 0, 5, ...]
        Only return the JSON list, no explanation.
        """
        
        try:
            response = await self.gemini.generate_content(
                model="gemini-2.0-flash", # Faster model for reranking
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            
            # Parse the list of indices
            rank_text = response.get("text", "[]")
            indices = json.loads(re.search(r'\[.*\]', rank_text, re.DOTALL).group())
            
            # Reorder candidates based on indices
            reranked = []
            seen = set()
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(candidates) and idx not in seen:
                    reranked.append(candidates[idx])
                    seen.add(idx)
                    
            # Add remaining items that weren't in top_n (optional, but good for completeness)
            for i in range(len(candidates)):
                if i not in seen:
                    reranked.append(candidates[i])
                    
            return reranked[:top_n]
        except Exception as e:
            logger.warning(f"Gemini reranking failed: {e}")
            return candidates[:top_n]

    async def _expand_context(self, filename: str, chunk_index: int, original_content: str) -> str:
        """Fetch +/- 1 chunk around the current hit to provide fuller context."""
        try:
            # We want to find chunks with the same filename and chunk_index in [idx-1, idx+1]
            indices = [chunk_index - 1, chunk_index + 1]
            
            # Use deterministic ID search or filter search
            # Filter search is more robust if IDs changed
            filter_search = models.Filter(
                must=[
                    models.FieldCondition(key="filename", match=models.MatchValue(value=filename)),
                    models.FieldCondition(key="chunk_index", match=models.MatchAny(any=indices))
                ]
            )
            
            # Search for these specific chunks
            neighbors = self.qdrant.scroll(
                collection_name=self.library_collection,
                scroll_filter=filter_search,
                limit=2,
                with_payload=True
            )[0]
            
            # Sort neighbors by chunk index
            neighbor_map = {p.payload["chunk_index"]: p.payload["content"] for p in neighbors}
            
            expanded = ""
            if chunk_index - 1 in neighbor_map:
                expanded += neighbor_map[chunk_index - 1] + "\n\n"
            
            expanded += original_content
            
            if chunk_index + 1 in neighbor_map:
                expanded += "\n\n" + neighbor_map[chunk_index + 1]
                
            return expanded
        except Exception as e:
            logger.warning(f"Context expansion failed for {filename} index {chunk_index}: {e}")
            return original_content

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

    async def ingest_library_book(self, filename: str, content: str, metadata: dict = None):
        """Ingest a quantitative finance book using QuantMarkdownSplitter with DB persistence."""
        db = SessionLocal()
        book_id = None
        try:
            # 1. Register in DB
            book = db.query(LibraryBook).filter(LibraryBook.filename == filename).first()
            if not book:
                book = LibraryBook(filename=filename, ingestion_status=IngestionStatus.PENDING)
                db.add(book)
            else:
                book.ingestion_status = IngestionStatus.PENDING
                book.last_ingested_at = datetime.utcnow()
            
            db.commit()
            db.refresh(book)
            book_id = book.id

            # 2. Split and Ingest
            splitter = QuantMarkdownSplitter(max_chunk_size=3000)
            chunks = splitter.split_text(content)
            
            book.total_chunks = len(chunks)
            db.commit()

            points = []
            sem = asyncio.Semaphore(5)

            async def process_chunk(i, chunk_text):
                async with sem:
                    try:
                        embedding = await self._get_embedding(chunk_text)
                        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"lib_{filename}_chunk_{i}"))
                        
                        return models.PointStruct(
                            id=chunk_id,
                            vector=embedding,
                            payload={
                                "filename": filename,
                                "content": chunk_text,
                                "doc_type": "library_book",
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                **(metadata or {})
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to embed book chunk {i}: {e}")
                        return None

            tasks = [process_chunk(i, c) for i, c in enumerate(chunks)]
            results = await asyncio.gather(*tasks)
            points = [p for p in results if p is not None]
            
            if points:
                batch_size = 50
                for i in range(0, len(points), batch_size):
                    self.qdrant.upsert(
                        collection_name=self.library_collection,
                        points=points[i:i + batch_size]
                    )
                
                # Update status
                book.ingestion_status = IngestionStatus.INGESTED
                book.last_ingested_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Ingested library book: {filename} ({len(points)} chunks)")
            else:
                book.ingestion_status = IngestionStatus.FAILED
                db.commit()
                logger.warning(f"No chunks ingested for book: {filename}")

        except Exception as e:
            logger.error(f"Book ingestion failed for {filename}: {e}")
            if book_id:
                book = db.query(LibraryBook).filter(LibraryBook.id == book_id).first()
                if book:
                    book.ingestion_status = IngestionStatus.FAILED
                    db.commit()
            raise
        finally:
            db.close()
