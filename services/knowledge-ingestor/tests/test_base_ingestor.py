import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
from app.base_ingestor import BaseIngestor
from app.core.models import IngestionResult


class MockIngestor(BaseIngestor):
    async def run_pipeline(self, file_path: Path) -> IngestionResult:
        return IngestionResult(filename=file_path.name, status="complete")


class TestBaseIngestor(unittest.TestCase):
    def setUp(self):
        # Mock FalkorDBClient to avoid connection attempts
        with patch("app.base_ingestor.FalkorDBClient") as mock_client:
            self.ingestor = MockIngestor("TestIngestor")
            self.mock_db = mock_client.return_value

    def test_scan_files(self):
        with patch("app.core.app_config.config") as mock_config:
            mock_config.source_dir = Path("/tmp/source")
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.iterdir") as mock_iter,
            ):
                file1 = MagicMock(spec=Path)
                file1.is_file.return_value = True
                file1.suffix = ".md"
                file1.name = "test.md"

                mock_iter.return_value = [file1]

                files = self.ingestor.scan_files()
                self.assertEqual(len(files), 1)
                self.assertEqual(files[0].name, "test.md")

    def test_scan_files_not_found(self):
        with patch("app.core.app_config.config") as mock_config:
            mock_config.source_dir = Path("/non/existent")
            with patch("pathlib.Path.exists", return_value=False):
                files = self.ingestor.scan_files()
                self.assertEqual(files, [])

    @patch("shutil.copy2")
    @patch("os.remove")
    def test_archive_file(self, mock_remove, mock_copy):
        file_path = Path("source_data/test.md")
        with patch("app.core.app_config.config") as mock_config:
            mock_config.archive_dir = Path("/tmp/archive")
            result = self.ingestor.archive_file(file_path)
            self.assertTrue(result)
            mock_copy.assert_called()
            mock_remove.assert_called()

    @patch("shutil.move")
    @patch("builtins.open", new_callable=mock_open)
    def test_move_to_errors(self, mock_file, mock_move):
        file_path = Path("source_data/test.md")
        with patch("app.core.app_config.config") as mock_config:
            mock_config.error_dir = Path("/tmp/errors")
            result = self.ingestor.move_to_errors(file_path, "Error message")
            self.assertTrue(result)
            mock_move.assert_called()
            mock_file.assert_called()

    @patch("app.base_ingestor.BaseIngestor.scan_files")
    def test_run(self, mock_scan):
        mock_scan.return_value = [Path("source_data/test.md")]

        # Use patch.object on the instance with AsyncMock
        with patch.object(
            self.ingestor, "run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            mock_pipeline.return_value = IngestionResult(
                filename="test.md", status="complete"
            )

            with patch.object(self.ingestor, "archive_file") as mock_archive:
                self.ingestor.run(max_concurrent=1)
                mock_archive.assert_called_once()

    @patch("app.base_ingestor.BaseIngestor.scan_files")
    def test_run_with_exception(self, mock_scan):
        mock_scan.return_value = [Path("source_data/error.md")]

        with patch.object(
            self.ingestor, "run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            mock_pipeline.side_effect = Exception("Failure")

            with patch.object(self.ingestor, "move_to_errors") as mock_error:
                self.ingestor.run(max_concurrent=1)
                mock_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
