import unittest
from unittest.mock import MagicMock, patch
from app.tools.falkordb_client import FalkorDBClient

class TestFalkorDBClient(unittest.TestCase):
    def setUp(self):
        # Clear the connection pool to ensure clean state for each test
        FalkorDBClient._connection_pool = {}
        self.client = FalkorDBClient(host="localhost", port=6380, graph_name="TestGraph")

    @patch("redis.Redis")
    def test_connect_success(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        result = self.client.connect()
        self.assertEqual(result["status"], "connected")
        mock_instance.ping.assert_called_once()

    @patch("redis.Redis")
    def test_connect_failure(self, mock_redis):
        mock_redis.side_effect = Exception("Connection error")
        
        result = self.client.connect()
        self.assertEqual(result["status"], "error")
        self.assertIn("Connection error", result["message"])

    @patch("redis.Redis")
    def test_execute_query(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        self.client.connect()
        
        mock_instance.execute_command.return_value = "Result"
        result = self.client.execute_query("MATCH (n) RETURN n")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "Result")
        mock_instance.execute_command.assert_called_with("GRAPH.QUERY", "TestGraph", "MATCH (n) RETURN n")

    @patch("redis.Redis")
    def test_execute_batch(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        self.client.connect()
        
        mock_pipeline = MagicMock()
        mock_instance.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = ["res1", "res2"]
        
        queries = ["CREATE (a)", "CREATE (b)"]
        result = self.client.execute_batch(queries)
        
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["success"], 2)
        self.assertEqual(len(result["results"]), 2)

    @patch("redis.Redis")
    def test_get_stats(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        self.client.connect()
        
        mock_instance.execute_command.return_value = "Stats"
        result = self.client.get_stats()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["info"], "Stats")

    @patch("redis.Redis")
    def test_execute_query_failure(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        self.client.connect()
        
        mock_instance.execute_command.side_effect = Exception("Query failed")
        result = self.client.execute_query("INVALID")
        self.assertEqual(result["status"], "error")
        self.assertIn("Query failed", result["message"])

    def test_execute_batch_empty(self):
        result = self.client.execute_batch([])
        self.assertEqual(result["success"], 0)
        self.assertEqual(result["failed"], 0)

    @patch("redis.Redis")
    def test_get_stats_error(self, mock_redis):
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        self.client.connect()
        mock_instance.execute_command.side_effect = Exception("No stats")
        result = self.client.get_stats()
        self.assertEqual(result["status"], "error")
        self.assertIn("No stats", result["message"])

if __name__ == "__main__":
    unittest.main()
