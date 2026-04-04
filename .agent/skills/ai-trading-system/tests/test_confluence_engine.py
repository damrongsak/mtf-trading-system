import sys
import os
import unittest

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.orchestrator.confluence_score_engine import ConfluenceScoreEngine

class TestConfluenceEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ConfluenceScoreEngine()

    def test_authorization(self):
        # Spec says score >= 7 is required for authorization.
        # Placeholder returns 1 + 2 + 2 + 2 = 7 by default.
        res = self.engine.calculate_score({})
        self.assertEqual(res.score, 7)
        self.assertTrue(res.is_authorized)

if __name__ == '__main__':
    unittest.main()
