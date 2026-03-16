import unittest
from unittest.mock import patch, MagicMock
from app.core.llm_utils import LLMUtils

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
        response = 'Invalid stuff { not a json'
        result = LLMUtils.parse_json_response(response)
        self.assertIn("error", result)

    def test_parse_json_fixed(self):
        """Test parsing JSON with unescaped newlines"""
        response = '{"key": "value\nwith newline"}'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(result.get("key"), "value\nwith newline")

    def test_parse_cypher_queries_manual(self):
        """Test manual extraction of cypher_queries array"""
        response = 'Some talk "cypher_queries": ["MATCH (n) RETURN n", "CREATE (n)"]'
        result = LLMUtils.parse_json_response(response)
        self.assertEqual(len(result.get("cypher_queries", [])), 2)

    @patch("app.core.llm_utils.asyncio.to_thread")
    async def test_call_llm_success(self, mock_to_thread):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "ok"}'}}]
        }
        mock_to_thread.return_value = mock_response
        
        from app.core.app_config import config
        config.openrouter_api_key = "test_key"
        
        result = await LLMUtils.call_llm("sys", "user")
        self.assertEqual(result.get("result"), "ok")

    @patch("app.core.llm_utils.asyncio.to_thread")
    async def test_call_llm_api_error(self, mock_to_thread):
        from app.core.app_config import config
        config.openrouter_api_key = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_to_thread.return_value = mock_response
    
        result = await LLMUtils.call_llm("sys", "user")
        self.assertIn("error", result)
        self.assertIn("API error: 500", result["error"])

    @patch("app.core.llm_utils.asyncio.to_thread")
    async def test_call_llm_fallback_success(self, mock_to_thread):
        """Test that LLM falls back to second model on first failure"""
        from app.core.app_config import config
        config.openrouter_api_key = "test_key"
        config.model_name = "first-model"
        config.fallback_model_name = "fallback-model"
        
        # First call fails, second succeeds
        mock_fail = MagicMock()
        mock_fail.status_code = 400
        mock_fail.text = "Bad Request"
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "choices": [{"message": {"content": '{"result": "fallback_ok"}'}}]
        }
        
        mock_to_thread.side_effect = [mock_fail, mock_success]
        
        result = await LLMUtils.call_llm("sys", "user")
        self.assertEqual(result.get("result"), "fallback_ok")
        self.assertEqual(mock_to_thread.call_count, 2)
        
        # Verify first call used first-model
        args, kwargs = mock_to_thread.call_args_list[0]
        # First arg after mock_to_thread, func, is requests.post. 
        # The args passed to requests.post are in args[1:] or kwargs.
        # But wait, asyncio.to_thread(func, *args, **kwargs)
        # So call_args will be (requests.post, url, ...)
        self.assertEqual(kwargs['json']['model'], "first-model")
        
        # Verify second call used fallback-model
        args, kwargs = mock_to_thread.call_args_list[1]
        self.assertEqual(kwargs['json']['model'], "fallback-model")

    async def test_call_llm_no_key(self):
        from app.core.app_config import config
        config.openrouter_api_key = None
        result = await LLMUtils.call_llm("sys", "user")
        self.assertIn("error", result)

if __name__ == "__main__":
    unittest.main()
