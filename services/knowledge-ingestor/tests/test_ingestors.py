import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.ingestors.orchestrator import OlympusOrchestrator
from app.ingestors.hierarchical_ingestor import HierarchicalIngestor

class TestIngestors(unittest.IsolatedAsyncioTestCase):
    
    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_orchestrator_pipeline(self, mock_llm):
        # Mock LLM transitions
        mock_llm.side_effect = [
            {"cypher_queries": ["CREATE (p:Paper {title: 'Test'})"]}, # Planner
            {"cypher_queries": ["CREATE (p:Paper {title: 'Test'})"]}, # Architect
            {"success": 1, "failed": 0} # Executor (returns DB result)
        ]
        
        from unittest.mock import mock_open
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            with patch("builtins.open", mock_open(read_data="test content")):
                with patch("app.base_ingestor.BaseIngestor.execute_to_falkor") as mock_db:
                    mock_db.return_value = {"success": 1, "failed": 0}
                    
                    orch = OlympusOrchestrator()
                    res = await orch.run_pipeline(Path("source_data/test.md"))
                    
                    self.assertEqual(res.status, "complete")
                    self.assertEqual(mock_llm.call_count, 2)

    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_orchestrator_llm_error(self, mock_llm):
        mock_llm.return_value = {"error": "LLM Failure"}
        
        from unittest.mock import mock_open
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            with patch("builtins.open", mock_open(read_data="test content")):
                orch = OlympusOrchestrator()
                res = await orch.run_pipeline(Path("source_data/test.md"))
                self.assertEqual(res.status, "failed")

    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_orchestrator_json_truncation(self, mock_llm):
        mock_llm.return_value = {"cypher_queries": ["MATCH (n) RETURN n"]}
        
        from unittest.mock import mock_open
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 1000
            # Mock a very long JSON string
            long_json = '{"data": "' + 'x' * 90000 + '"}'
            with patch("builtins.open", mock_open(read_data=long_json)):
                with patch("app.base_ingestor.BaseIngestor.execute_to_falkor") as mock_db:
                    mock_db.return_value = {"success": 1}
                    orch = OlympusOrchestrator()
                    res = await orch.run_pipeline(Path("source_data/test.json"))
                    self.assertEqual(res.status, "complete")

    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_hierarchical_pipeline(self, mock_llm):
        # Mock LLM transitions for Summary, Detail, Conclusion, AND Committer
        mock_llm.side_effect = [
            {"cypher_queries": ["CREATE (s:Summary)"]}, # Summary
            {"cypher_queries": ["CREATE (d:Detail)"]},  # Detail
            {"cypher_queries": ["CREATE (c:Conclusion)"]}, # Conclusion
            {"final_nodes": ["Asset1"], "merge_notes": "Clean", "cypher_queries": ["CREATE (m:Merged)"]}, # Committer
            {"search_required": False} # WebScout
        ]
        
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="test content")))))):
            with patch("app.base_ingestor.BaseIngestor.execute_to_falkor") as mock_db:
                mock_db.return_value = {"success": 4, "failed": 0}
                
                hi = HierarchicalIngestor()
                res = await hi.run_pipeline(Path("source_data/test.md"))
                
                self.assertEqual(res.status, "complete")
                self.assertEqual(mock_llm.call_count, 5) # Summary, Detail, Conclusion, Committer, WebScout

    async def test_hierarchical_splitting(self):
        """Test the logic of read_file_tiers with varied content"""
        hi = HierarchicalIngestor()
        content = "Summary\n" + "="*50 + "\nDetail\n" + "="*50 + "\nConclusion"
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=content)))))):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 100
                tiers = hi.read_file_tiers(Path("test.md"))
                self.assertIn("summary", tiers["tiers"])
                self.assertIn("detail", tiers["tiers"])

    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_hierarchical_large_document(self, mock_llm):
        """Test hierarchical ingestor with many chunks (triggering chunking logic)"""
        # Mock LLM for: 1 Summary, 2 Detail Chunks, 1 Conclusion, 1 Committer
        mock_llm.side_effect = [
            {"cypher_queries": ["S1"]}, # Summary
            {"cypher_queries": ["D1"], "nodes": [{"name": "N1"}]}, # Detail Chunk 1
            {"cypher_queries": ["D2"], "nodes": [{"name": "N2"}]}, # Detail Chunk 2
            {"cypher_queries": ["C1"]}, # Conclusion
            {"final_nodes": ["N1"], "merge_notes": "notes", "cypher_queries": ["M1"], "deduplication_stats": {"nodes_removed": 0}}, # Committer
            {"search_required": False} # WebScout
        ]
        
        # Create a large document with headings to trigger chunking
        # self.detail_chars is 60,000. We need detail section > 60KB.
        large_content = "Summary\n" + "="*50 + "\n"
        large_content += "## Heading 1\n" + "x" * 40000 + "\n"
        large_content += "## Heading 2\n" + "y" * 40000 + "\n"
        large_content += "="*50 + "\nConclusion"
        
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=large_content)))))):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(large_content)
                with patch("app.base_ingestor.BaseIngestor.execute_to_falkor") as mock_db:
                    mock_db.return_value = {"success": 1}
                    
                    hi = HierarchicalIngestor()
                    # Override the threshold to make it easier to trigger in test if needed,
                    # but here we just use large content.
                    res = await hi.run_pipeline(Path("large.md"))
                    
                    self.assertEqual(res.status, "complete")
                    # Counts: summary(1) + detail(2) + conclusion(1) + committer(1) + webscout(1) = 6
                    self.assertEqual(mock_llm.call_count, 6)

    async def test_orchestrator_pdf_csv(self, mock_llm=None):
        """Test reading PDF and CSV files"""
        orch = OlympusOrchestrator()
        
        # Test PDF branch
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            res = orch.read_file(Path("test.pdf"))
            self.assertIn("PDF", res["content"])

        # Test CSV branch
        csv_content = "col1,col2\nval1,val2\nval3,val4"
        from unittest.mock import mock_open
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            with patch("builtins.open", mock_open(read_data=csv_content)):
                res = orch.read_file(Path("test.csv"))
                self.assertIn("col1,col2", res["content"])

    async def test_orchestrator_csv_truncation(self):
        """Test CSV truncation logic"""
        orch = OlympusOrchestrator()
        # Header + many rows to trigger truncation
        csv_content = "header\n" + "row\n" * 1000
        from unittest.mock import mock_open
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 5000
            with patch("builtins.open", mock_open(read_data=csv_content)):
                # Small max_chars to force truncation
                res = orch.read_file(Path("test.csv"), max_chars=100)
                self.assertTrue(res["chunk_info"]["truncated"])

    @patch("app.core.llm_utils.LLMUtils.call_llm")
    async def test_hierarchical_committer_error(self, mock_llm):
        """Test hierarchical ingestor when committer fails"""
        mock_llm.side_effect = [
            {"cypher_queries": ["Q1"]}, # Summary
            {"cypher_queries": ["Q2"]}, # Detail
            {"cypher_queries": ["Q3"]}, # Conclusion
            {"error": "Committer failed"}, # Committer (Pipeline fails immediately, WebScout not called)
            {"search_required": False} # Buffer
        ]
        
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="content")))))):
            hi = HierarchicalIngestor()
            res = await hi.run_pipeline(Path("test.md"))
            self.assertEqual(res.status, "failed")

if __name__ == "__main__":
    unittest.main()
