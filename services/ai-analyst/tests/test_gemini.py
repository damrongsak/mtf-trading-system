import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gemini import GeminiClient

@pytest.mark.asyncio
async def test_gemini_client_byok_override():
    # Setup Mocks
    mock_default_client = AsyncMock()
    mock_custom_client = AsyncMock()
    
    mock_factory = MagicMock()
    mock_factory.side_effect = lambda api_key: mock_custom_client if api_key == "custom-key" else mock_default_client
    
    with patch("app.services.gemini.settings") as mock_settings:
        mock_settings.gemini.api_key = "system-key"
        mock_settings.gemini.model_id = "system-model"
        
        # Inject factory
        client = GeminiClient(client_factory=mock_factory)
        
        # Initial init should call factory with system key
        # (Our lambda logic above checks key, but let's verify calls later)
        
        # Method under test
        await client.generate_market_outlook({}, api_key="custom-key", model_id="custom-model")
        
        # Verify factory called with custom key
        mock_factory.assert_called_with(api_key="custom-key")
        
        # Verify custom client usage
        mock_custom_client.aio.models.generate_content.assert_called_once()
        args = mock_custom_client.aio.models.generate_content.call_args
        assert args.kwargs['model'] == "custom-model"

@pytest.mark.asyncio
async def test_gemini_client_default():
    mock_default_client = AsyncMock()
    mock_factory = MagicMock(return_value=mock_default_client)
    
    with patch("app.services.gemini.settings") as mock_settings:
        mock_settings.gemini.api_key = "system-key"
        mock_settings.gemini.model_id = "system-model"
        
        client = GeminiClient(client_factory=mock_factory)
        
        await client.generate_market_outlook({})
        
        # Verify default client usage
        # (self.client was initialized with mock_default_client)
        mock_default_client.aio.models.generate_content.assert_called_once()
