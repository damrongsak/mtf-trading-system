"""
Olympus Service Factory - Centralized Lazy Singletons
Prevents circular imports between API and Workers.
"""

from app.core.logging_config import get_logger

logger = get_logger("OlympusFactory")

_ingestor = None
_linter = None


def get_ingestor():
    """Lazy-initialize the Hierarchical Ingestor."""
    global _ingestor
    if _ingestor is None:
        from app.ingestors.hierarchical_ingestor import HierarchicalIngestor

        logger.info("Initializing HierarchicalIngestor singleton...")
        _ingestor = HierarchicalIngestor()
    return _ingestor


def get_linter():
    """Lazy-initialize the Graph Linter."""
    global _linter
    if _linter is None:
        from app.core.graph_linter import GraphLinter

        logger.info("Initializing GraphLinter singleton...")
        _linter = GraphLinter()
    return _linter
