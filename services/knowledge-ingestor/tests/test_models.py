import unittest
from app.core.models import ChunkResult, IngestionResult, HierarchicalResult


class TestModels(unittest.TestCase):
    def test_chunk_result(self):
        res = ChunkResult(tier="summary", cypher_queries=["CREATE (...)"])
        self.assertEqual(res.tier, "summary")
        self.assertEqual(len(res.cypher_queries), 1)
        self.assertEqual(res.node_count, 0)

    def test_ingestion_result(self):
        res = IngestionResult(filename="test.md", status="complete")
        self.assertEqual(res.filename, "test.md")
        self.assertEqual(res.status, "complete")

    def test_hierarchical_result(self):
        res = HierarchicalResult(
            filename="test.md", status="complete", category="macro"
        )
        self.assertEqual(res.category, "macro")
        self.assertEqual(res.status, "complete")


if __name__ == "__main__":
    unittest.main()
