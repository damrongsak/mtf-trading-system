from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ChunkResult:
    """Result from processing a single chunk or tier"""
    tier: str
    cypher_queries: List[str] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    tokens_used: int = 0
    raw_response: str = ""
    error: Optional[str] = None

@dataclass
class IngestionResult:
    """Overall result for a single file ingestion"""
    filename: str
    status: str  # "complete", "failed", "partial"
    planner_result: Optional[Dict[str, Any]] = None
    architect_result: Optional[Dict[str, Any]] = None
    committer_result: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    error: Optional[str] = None

@dataclass
class HierarchicalResult(IngestionResult):
    """Specific result for hierarchical processing (3-tier)"""
    summary_queries: List[str] = field(default_factory=list)
    detail_queries: List[str] = field(default_factory=list)
    conclusion_queries: List[str] = field(default_factory=list)
    category: str = "unknown"
    priority: str = "medium"
    confidence_score: float = 1.0  # Normalized 0.0-1.0
