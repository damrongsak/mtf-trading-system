import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.gemini import GeminiClient

# Fixture to mock the settings and ensure GOOGLE_API_KEY is set
@pytest.fixture
def mock_settings():
    with patch("app.services.gemini.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "fake_test_key"
        mock_settings.GEMINI_MODEL_ID = "gemini-1.5-flash-test"
        yield mock_settings

# Fixture to mock the genai.Client and its async methods
@pytest.fixture
def mock_genai_client():
    with patch("app.services.gemini.genai.Client") as mock_client_cls:
        # Create a mock instance of the Client
        mock_instance = MagicMock()
        
        # Structure: client.aio.models.generate_content
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_generate_content = AsyncMock()
        
        mock_instance.aio = mock_aio
        mock_aio.models = mock_models
        mock_models.generate_content = mock_generate_content
        
        # Ensure Client() returns this mock instance
        mock_client_cls.return_value = mock_instance
        
        # Yield the mocked generate_content method for assertions
        yield mock_generate_content

@pytest.mark.asyncio
async def test_generate_market_outlook_success(mock_settings, mock_genai_client):
    """
    Test that generate_market_outlook returns the text from the API response
    and calls the API with the correct context.
    """
    # 1. Setup Mock Return Value
    mock_response = MagicMock()
    mock_response.text = "## 📊 Market Context\nBased on the uptrend..."
    mock_genai_client.return_value = mock_response

    # 2. Initialize Service
    client = GeminiClient()

    # 3. Call Method
    context = {
        "trend_4h": "Uptrend",
        "current_price": "2050.00",
        "key_levels": ["2040", "2060"],
        "recent_signals": ["Buy Signal"]
    }
    result = await client.generate_market_outlook(context)

    # 4. Assertions
    assert "Based on the uptrend" in result
    
    # Verify the API was called exactly once
    mock_genai_client.assert_called_once()
    
    # Verify arguments
    _, kwargs = mock_genai_client.call_args
    # Check if initialized with correct model
    assert client.model_id == 'gemini-1.5-flash-test'
    
    # Mock the aio.models.generate_content method
    assert "Uptrend" in kwargs['contents']
    assert "2050.00" in kwargs['contents']

@pytest.mark.asyncio
async def test_generate_market_outlook_error(mock_settings, mock_genai_client):
    """
    Test that exceptions from the API are caught and returned as error messages.
    """
    # 1. Setup Mock to Raise Exception
    mock_genai_client.side_effect = Exception("API Connection Failed")

    # 2. Initialize Service
    client = GeminiClient()

    # 3. Call Method
    result = await client.generate_market_outlook({})

    # 4. Assertions
    assert "Error generating insight" in result
    assert "API Connection Failed" in result

@pytest.mark.asyncio
async def test_analyze_journal_entry_success(mock_settings, mock_genai_client):
    """
    Test analyze_journal_entry with mocked response.
    """
    mock_response = MagicMock()
    mock_response.text = "- Detected Emotion: FOMO"
    mock_genai_client.return_value = mock_response

    client = GeminiClient()
    
    entry = "I bought because prices were moving fast."
    similar = ["Past mistake: chasing candles"]
    
    result = await client.analyze_journal_entry(entry, similar)
    
    assert "Detected Emotion: FOMO" in result
    mock_genai_client.assert_called_once()
    _, kwargs = mock_genai_client.call_args
    assert "chasing candles" in kwargs['contents']
