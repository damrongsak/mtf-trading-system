import unittest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from app.base_ingestor import BaseIngestor
from app.core.models import IngestionResult

class MockIngestor(BaseIngestor):
    async def run_pipeline(self, file_path: Path) -> IngestionResult:
        return IngestionResult(filename=file_path.name, status="complete")

class TestBaseIngestor(unittest.TestCase):
    def setUp(self):
        self.ingestor = MockIngestor("TestIngestor")

    def test_scan_files(self):
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.iterdir") as mock_iter:
                file1 = MagicMock(spec=Path)
                file1.is_file.return_value = True
                file1.suffix = ".md"
                file1.name = "test.md"
                
                mock_iter.return_value = [file1]
                
                files = self.ingestor.scan_files()
                self.assertEqual(len(files), 1)
                self.assertEqual(files[0].name, "test.md")

    @patch("app.core.app_config.config")
    def test_scan_files_not_found(self, mock_config):
        mock_config.source_dir = Path("/non/existent")
        # Should return empty list and log warning
        files = self.ingestor.scan_files()
        self.assertEqual(files, [])

    @patch("shutil.move")
    def test_archive_file(self, mock_move):
        file_path = Path("source_data/test.md")
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            result = self.ingestor.archive_file(file_path)
            self.assertTrue(result)
            mock_move.assert_called()

    @patch("shutil.move")
    @patch("builtins.open", new_callable=mock_open)
    def test_move_to_errors(self, mock_file, mock_move):
        file_path = Path("source_data/test.md")
        result = self.ingestor.move_to_errors(file_path, "Error message")
        self.assertTrue(result)
        mock_move.assert_called()
        mock_file.assert_called()

    @patch("app.base_ingestor.BaseIngestor.scan_files")
    def test_run(self, mock_scan):
        mock_scan.return_value = [Path("source_data/test.md")]
        
        # We need to mock run_pipeline to return a result
        with patch.object(MockIngestor, 'run_pipeline', new_callable=MagicMock) as mock_pipeline:
            # Since it's awaited, we need to return a future/coroutine
            async def mock_ret(*args):
                return IngestionResult(filename="test.md", status="complete")
            mock_pipeline.side_effect = mock_ret
            
            with patch.object(self.ingestor, 'archive_file') as mock_archive:
                self.ingestor.run(max_concurrent=1)
                mock_archive.assert_called_once()

    @patch("app.base_ingestor.BaseIngestor.scan_files")
    def test_run_with_exception(self, mock_scan):
        mock_scan.return_value = [Path("source_data/error.md")]
        
        with patch.object(MockIngestor, 'run_pipeline', new_callable=MagicMock) as mock_pipeline:
            async def mock_err(*args):
                raise Exception("Failure")
            mock_pipeline.side_effect = mock_err
            
            with patch.object(self.ingestor, 'move_to_errors') as mock_error:
                self.ingestor.run(max_concurrent=1)
                mock_error.assert_called_once()

if __name__ == "__main__":
    unittest.main()
