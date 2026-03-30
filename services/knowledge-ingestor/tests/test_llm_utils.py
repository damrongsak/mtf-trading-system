import unittest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.llm_utils import LLMUtils
from app.core.app_config import config


class TestLLMUtils(unittest.IsolatedAsyncioTestCase):
    def test_parse_json_markdown(self):
        """Test parsing JSON from markdown blocks"""
        response = '```json\n{"key": "value"}\n```'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(result.get("key"), "value")

    def test_parse_json_raw(self):
        """Test parsing raw JSON string"""
        response = '{"key": "value"}'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(result.get("key"), "value")

    def test_parse_json_with_text(self):
        """Test parsing JSON with surrounding text"""
        response = 'Here is the data: {"key": "value"} Hope it helps!'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(result.get("key"), "value")

    def test_parse_json_error(self):
        """Test parsing invalid JSON"""
        response = "Invalid stuff { not a json"
        result = LLMUtils.parse_json_response(response)
        self.assertIn("error", result)

    def test_parse_json_fixed(self):
        """Test parsing JSON with unescaped newlines"""
        response = '{"key": "value\nwith newline"}'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(result.get("key"), "value\nwith newline")

    @patch("app.core.llm_utils.LLMUtils._try_openrouter")
    async def test_call_llm_success(self, mock_try_openrouter):
        """Test successful Tier 1 call"""
        mock_try_openrouter.return_value = ({"result": "ok"}, None)

        config.openrouter_api_key = "test_key"

        result = await LLMUtils.call_llm("sys", "user")
        self.assertEqual(result.get("result"), "ok")
        mock_try_openrouter.assert_called_once()

    @patch("app.core.llm_utils.LLMUtils._try_openrouter")
    @patch("app.core.llm_utils.LLMUtils._try_gemini_direct")
    async def test_call_llm_fallback_to_gemini(self, mock_gemini, mock_openrouter):
        """Test fallback through both OpenRouter tiers to Gemini"""
        config.openrouter_api_key = "test_key"
        config.google_api_key = "google_key"

        # Both OpenRouter tiers fail
        mock_openrouter.return_value = (None, "Provider failure")
        # Gemini succeeds
        mock_gemini.return_value = ({"result": "gemini_ok"}, None)

        result = await LLMUtils.call_llm("sys", "user")
        self.assertEqual(result.get("result"), "gemini_ok")
        self.assertEqual(mock_openrouter.call_count, 2)
        mock_gemini.assert_called_once()

    @patch("app.core.llm_utils._get_http_client")
    async def test_try_openrouter_http_error(self, mock_get_client):
        """Test provider helper handling HTTP errors"""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        result, err = await LLMUtils._try_openrouter(
            "model", "sys", "user", 1000, "tier-label"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(err)
        self.assertIn("HTTP 500", err or "")

    @patch("app.core.llm_utils._get_http_client")
    async def test_try_openrouter_network_error(self, mock_get_client):
        """Test provider helper handling network exceptions"""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.ConnectTimeout("Timeout")
        mock_get_client.return_value = mock_client

        result, err = await LLMUtils._try_openrouter(
            "model", "sys", "user", 1000, "tier-label"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(err)
        self.assertIn("Connect timeout", err or "")

    async def test_call_llm_no_keys(self):
        """Test behavior when no API keys are configured"""
        config.openrouter_api_key = None
        config.google_api_key = None

        result = await LLMUtils.call_llm("sys", "user")
        self.assertIn("error", result)
        self.assertIn("exhausted", result["error"])


if __name__ == "__main__":
    unittest.main()
