import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag import RAGService

@pytest.fixture
def mock_gemini():
    return MagicMock()

@pytest.fixture
def mock_qdrant():
    return MagicMock()

@pytest.mark.asyncio
async def test_ingest_document(mock_gemini):
    # Setup mocks
    embed_mock = AsyncMock()
    embed_mock.embedding = [0.1, 0.2, 0.3]
    mock_gemini.client.aio.models.embed_content = AsyncMock(return_value=embed_mock)
    
    with patch("app.services.rag.QdrantClient") as MockQdrant:
        mock_qdrant_instance = MockQdrant.return_value
        rag = RAGService(mock_gemini)
        
        # Override the mock with our specific needs if necessary, though patching class returns a mock by default
        # The internal self.qdrant is now mock_qdrant_instance
        
        await rag.ingest_document("test.md", "Content", doc_type="spec")
        
        # Verify embedding called
        mock_gemini.client.aio.models.embed_content.assert_called_once()
        
        # Verify Upsert 
        mock_qdrant_instance.upsert.assert_called_once()
        call_args = mock_qdrant_instance.upsert.call_args
        assert call_args.kwargs['collection_name'] == "system_docs"
        points = call_args.kwargs['points']
        assert len(points) == 1
        assert points[0].payload['filename'] == "test.md"

@pytest.mark.asyncio
async def test_search_documentation(mock_gemini):
    embed_mock = AsyncMock()
    embed_mock.embedding = [0.1, 0.2, 0.3]
    mock_gemini.client.aio.models.embed_content = AsyncMock(return_value=embed_mock)
    
    with patch("app.services.rag.QdrantClient") as MockQdrant:
        mock_qdrant_instance = MockQdrant.return_value
        rag = RAGService(mock_gemini)
        
        # Mock search result
        mock_hit = MagicMock()
        mock_hit.payload = {"filename": "test.md", "content": "Found"}
        mock_hit.score = 0.95
        mock_qdrant_instance.query_points.return_value.points = [mock_hit]
        
        results = await rag.search_documentation("query")
        
        assert len(results) == 1
        assert results[0]['filename'] == "test.md"
        mock_qdrant_instance.query_points.assert_called_once()
