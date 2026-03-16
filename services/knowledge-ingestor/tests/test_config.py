import unittest
from unittest.mock import patch
from app.core.app_config import config

class TestConfig(unittest.TestCase):
    def test_config_paths(self):
        """Verify that paths are correctly resolved"""
        self.assertTrue(config.source_dir.exists())
        self.assertTrue(config.archive_dir.exists())
        self.assertTrue(config.error_dir.exists())

    def test_config_defaults(self):
        """Verify default values"""
        self.assertEqual(config.graph_name, "OlympusKnowledgeGraph")
        self.assertIsInstance(config.falkor_port, int)

    def test_ensure_dirs_error(self):
        """Test directory creation failure (read-only path)"""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            # Re-instantiating will trigger mkdir
            from app.core.app_config import AppConfig
            with patch("app.core.app_config.logger") as mock_logger:
                AppConfig()
                mock_mkdir.assert_called()
                mock_logger.error.assert_called()

if __name__ == "__main__":
    unittest.main()
