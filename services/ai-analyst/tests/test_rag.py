import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag import RAGService
from qdrant_client.http import models

@pytest.fixture
def mock_qdrant():
    with patch("app.services.rag.QdrantClient") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_gemini():
    mock = MagicMock()
    # Mock the embedding call chain: client.aio.models.embed_content
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_embed = AsyncMock()
    
    mock.client.aio = mock_aio
    mock_aio.models = mock_models
    mock_models.embed_content = mock_embed
    
    # Default mock embedding return
    mock_result = MagicMock()
    mock_result.embedding = [0.1, 0.2, 0.3]
    mock_embed.return_value = mock_result
    
    return mock

@pytest.fixture
def rag_service(mock_qdrant, mock_gemini):
    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.QDRANT_HOST = "localhost"
        mock_settings.QDRANT_PORT = 6333
        return RAGService(gemini_client=mock_gemini)

def test_init_ensures_collection(mock_qdrant):
    # Setup: get_collection raises exception (simulating 404)
    mock_qdrant.get_collection.side_effect = Exception("Not Found")
    
    with patch("app.services.rag.settings"):
        RAGService()
        
    assert mock_qdrant.create_collection.call_count == 2
    
    # Check calls
    calls = mock_qdrant.create_collection.call_args_list
    assert calls[0].kwargs['collection_name'] == "journal_entries"
    assert calls[1].kwargs['collection_name'] == "strategies"

@pytest.mark.asyncio
async def test_ingest_journal_entry(rag_service, mock_gemini, mock_qdrant):
    entry_id = "test-id-123"
    content = "I felt FOMO."
    user_id = "user-1"
    
    await rag_service.ingest_journal_entry(entry_id, content, user_id=user_id)
    
    # verify embedding call
    mock_gemini.client.aio.models.embed_content.assert_called_once()
    
    # verify upsert
    mock_qdrant.upsert.assert_called_once()
    args, kwargs = mock_qdrant.upsert.call_args
    assert kwargs['collection_name'] == "journal_entries"
    points = kwargs['points']
    assert len(points) == 1
    assert points[0].payload['content'] == content
    assert points[0].payload['original_id'] == entry_id
    assert points[0].payload['user_id'] == user_id

@pytest.mark.asyncio
async def test_search_similar_entries(rag_service, mock_gemini, mock_qdrant):
    # Setup mock search result
    mock_hit = MagicMock()
    mock_hit.payload = {"content": "Old FOMO entry"}
    mock_qdrant.search.return_value = [mock_hit]
    
    user_id = "user-1"
    results = await rag_service.search_similar_entries("new query", user_id=user_id)
    
    assert len(results) == 1
    assert results[0] == "Old FOMO entry"
    
    # Verify search params
    mock_qdrant.search.assert_called_once()
    args, kwargs = mock_qdrant.search.call_args
    assert kwargs['limit'] == 3
    
    # Verify filter
    query_filter = kwargs['query_filter']
    assert query_filter is not None
    # Depending on how the object is structured/mocked, we might not be able to deeply assert properties easily 
    # without complex inspection, but we can verify it was passed.
    # For now, simplistic check:
    assert isinstance(query_filter, models.Filter)

@pytest.mark.asyncio
async def test_search_similar_strategies(rag_service, mock_gemini, mock_qdrant):
    # Setup mock search result
    mock_hit = MagicMock()
    mock_hit.payload = {"code": "def strategy(): pass", "stats": {"sharpe": 2.0}}
    mock_hit.score = 0.95
    mock_qdrant.search.return_value = [mock_hit]
    
    user_id = "user-1"
    results = await rag_service.search_similar_strategies("moving average", user_id=user_id)
    
    assert len(results) == 1
    assert results[0]["code"] == "def strategy(): pass"
    assert results[0]["score"] == 0.95
    
    mock_qdrant.search.assert_called_once()
    assert mock_qdrant.search.call_args[1]['collection_name'] == "strategies"
