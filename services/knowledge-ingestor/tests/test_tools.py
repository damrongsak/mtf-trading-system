import unittest
import json
from unittest.mock import patch, MagicMock
from app.tools.falkordb_client import falkordb_connect, falkordb_query, falkordb_batch

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

if __name__ == "__main__":
    unittest.main()
