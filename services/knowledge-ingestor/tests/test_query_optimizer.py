import unittest
from app.core.query_optimizer import deduplicate_cypher_queries


class TestQueryOptimizer(unittest.TestCase):
    def test_deduplicate_exact(self):
        queries = [
            "MERGE (n:Asset {name: 'XAUUSD'})",
            "MERGE (n:Asset {name: 'XAUUSD'})",
        ]
        result = deduplicate_cypher_queries(queries)
        self.assertEqual(len(result), 1)

    def test_merge_properties(self):
        queries = [
            "MERGE (n:Asset {name: 'XAUUSD', type: 'COMMODITY'})",
            "MERGE (n:Asset {name: 'XAUUSD', ticker: 'XAUUSD'})",
        ]
        result = deduplicate_cypher_queries(queries)
        self.assertEqual(len(result), 1)
        # Verify both properties exist in the merged query
        self.assertIn("type: 'COMMODITY'", result[0])
        self.assertIn("ticker: 'XAUUSD'", result[0])

    def test_non_merge_queries(self):
        queries = ["MATCH (n) RETURN n", "CREATE (a:Test {id: 1})"]
        result = deduplicate_cypher_queries(queries)
        self.assertEqual(len(result), 2)
        self.assertIn("MATCH (n) RETURN n", result)

    def test_mixed_queries(self):
        queries = [
            "MERGE (n:Asset {name: 'BTC'})",
            "MATCH (n:Asset {name: 'BTC'}) RETURN n",
            "MERGE (n:Asset {name: 'BTC', status: 'active'})",
        ]
        result = deduplicate_cypher_queries(queries)
        # Should have 1 merged node + 1 match
        self.assertEqual(len(result), 2)

    def test_empty_input(self):
        self.assertEqual(deduplicate_cypher_queries([]), [])
        self.assertEqual(deduplicate_cypher_queries(None), [])


if __name__ == "__main__":
    unittest.main()
