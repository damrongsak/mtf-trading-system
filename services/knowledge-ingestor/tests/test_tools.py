import unittest
import json
from unittest.mock import patch, MagicMock
from app.tools.falkordb_client import falkordb_connect, falkordb_query, falkordb_batch
from app.tools.web_search import WebSearchTool
from app.tools.web_scraper import WebScraperTool
from app.tools.market_reader import MarketReaderTool


class TestTools(unittest.TestCase):
    def setUp(self):
        # Clear the connection pool to ensure clean state for each test
        from app.tools.falkordb_client import FalkorDBClient

        FalkorDBClient._connection_pool = {}

    @patch("redis.Redis")
    def test_falkordb_connect_wrapper(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True

        res_str = falkordb_connect()
        res = json.loads(res_str)
        self.assertEqual(res["status"], "connected")

    @patch("redis.Redis")
    def test_falkordb_query_wrapper(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.execute_command.return_value = "Result"

        res_str = falkordb_query("MATCH (n) RETURN n")
        res = json.loads(res_str)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["result"], "Result")

    @patch("redis.Redis")
    def test_falkordb_batch_wrapper(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True

        mock_pipeline = MagicMock()
        mock_instance.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = ["res1", "res2"]

        res_str = falkordb_batch(["Q1", "Q2"])
        res = json.loads(res_str)
        self.assertEqual(res["total"], 2)
        self.assertEqual(res["success"], 2)


class TestWebTools(unittest.IsolatedAsyncioTestCase):
    @patch("app.tools.web_search.get_cache_region")
    @patch("asyncio.to_thread")
    async def test_web_search(self, mock_to_thread, mock_cache):
        # Mock Cache Region
        mock_region = MagicMock()
        from dogpile.cache.api import NO_VALUE

        mock_region.get.return_value = NO_VALUE
        mock_cache.return_value = mock_region

        # Mock results returned by the thread
        mock_to_thread.return_value = [
            {"title": "Title 1", "body": "Snippet 1", "href": "http://url1.com"},
            {"title": "Title 2", "body": "Snippet 2", "href": "http://url2.com"},
        ]

        results = await WebSearchTool.search("test query", max_results=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Title 1")
        self.assertEqual(results[0]["url"], "http://url1.com")

    @patch("httpx.AsyncClient.get")
    async def test_web_scraper(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = (
            "<html><body><h1>Hello World</h1><p>Test content</p></body></html>"
        )
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        text = await WebScraperTool.scrape_url("http://example.com")
        self.assertIsNotNone(text)
        if text:
            self.assertIn("Hello World", text)
            self.assertIn("Test content", text)


class TestMarketTools(unittest.IsolatedAsyncioTestCase):
    @patch("app.tools.market_reader.get_cache_region")
    @patch("httpx.AsyncClient.get")
    async def test_market_reader_success(self, mock_get, mock_region):
        from dogpile.cache.api import NO_VALUE
        mock_region.return_value.get.return_value = NO_VALUE
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {"result": [{"meta": {"regularMarketPrice": 2500.5}}]}
        }
        mock_get.return_value = mock_response

        price = await MarketReaderTool.get_spot_price("Gold")
        self.assertEqual(price, 2500.5)

    @patch("httpx.AsyncClient.get")
    async def test_market_reader_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        price = await MarketReaderTool.get_spot_price("Unknown")
        self.assertIsNone(price)


if __name__ == "__main__":
    unittest.main()
