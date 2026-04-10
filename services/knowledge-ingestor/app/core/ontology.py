"""
Standardized Ontology for Project Olympus Knowledge Graph.
Defines the allowed Node types, Relationship types, and their properties.
"""

from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field

# --- Allowed Labels and Types ---

NodeLabel = Literal[
    "Paper",
    "Source",  # Added for alignment
    "Asset",
    "Ticker",  # Added for alignment
    "Indicator", # Added for alignment
    "Concept",
    "MacroIndicator",
    "Event",
    "Strategy",
    "Organization",
    "Country",
    "Person",
    "SMC_Pattern",
    "Timeframe",
]

RelationshipType = Literal[
    "MENTIONS",
    "COVERS",  # Added for alignment
    "PREREQUISITE", # Added for alignment
    "INFLUENCES",
    "SUPPORTS",
    "CONTRADICTS",
    "TRIGGERS",
    "CORRELATES_WITH",
    "PROPOSES_STRATEGY",
    "AFFECTS",
    "LEADS_TO",
    "OBSERVED_IN",
    "HEDGE_AGAINST",
    "LIQUIDATES",
]

# --- Entity Resolution (Synonyms) ---

ENTITY_ALIASES = {
    # Organizations
    "fed": "Federal Reserve",
    "federal reserve": "Federal Reserve",
    "ecb": "European Central Bank",
    "european central bank": "European Central Bank",
    "boe": "Bank of England",
    "pbo": "People's Bank of China",
    "pboc": "People's Bank of China",
    # Assets
    "gold": "Gold",
    "xau": "Gold",
    "xauusd": "Gold",
    "bitcoin": "Bitcoin",
    "btc": "Bitcoin",
    "btcusd": "Bitcoin",
    "silver": "Silver",
    "xag": "Silver",
    "xagusd": "Silver",
    "wti": "Crude Oil",
    "crude": "Crude Oil",
    "oil": "Crude Oil",
    # Countries/Regions
    "us": "United States",
    "usa": "United States",
    "uk": "United Kingdom",
    "eu": "European Union",
}


def resolve_entity_name(name: str) -> str:
    """Normalize and resolve synonyms to canonical names."""
    clean_name = name.strip().lower()
    return ENTITY_ALIASES.get(clean_name, name.strip())


# --- Schema Definitions ---


class NodeSchema(BaseModel):
    """Blueprint for a single node in the graph"""

    label: NodeLabel = Field(..., description="The classification of the entity")
    name: str = Field(
        ...,
        description="The primary identifier/name of the entity (use PascalCase or formal names)",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., type, source, value, confidence)",
    )


class RelationshipSchema(BaseModel):
    """Blueprint for a relationship between two nodes"""

    from_node: str = Field(..., description="The 'name' of the source node")
    to_node: str = Field(..., description="The 'name' of the target node")
    type: RelationshipType = Field(..., description="The type of the relationship")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship metadata (e.g., confidence, source_ref, impact)",
    )


class GraphExtractionSchema(BaseModel):
    """Final output schema for the LLM to provide structured data"""

    thought_process: str = Field(
        ...,
        description="Professional analysis of identified entities and their structural links",
    )
    nodes: List[NodeSchema] = Field(
        default_factory=list, description="List of entities identified"
    )
    relationships: List[RelationshipSchema] = Field(
        default_factory=list, description="List of connections identified"
    )

    def to_cypher(self) -> List[str]:
        """Convert structured schema into valid Cypher queries"""
        queries = []

        # 1. Create Nodes
        for node in self.nodes:
            canonical_name = resolve_entity_name(node.name)
            safe_name = canonical_name.replace("'", "\\'")
            props_list = [f"name: '{safe_name}'"]
            for k, v in node.properties.items():
                if isinstance(v, str):
                    v = str(v).replace("'", "\\'")
                props_list.append(f"{k}: '{v}'")

            props_str = ", ".join(props_list)
            queries.append(
                f"MERGE (n:{node.label} {{name: '{safe_name}'}}) ON CREATE SET n += {{{', '.join(props_list)}}}"
            )

        # 2. Create Relationships
        for rel in self.relationships:
            props_list = []
            for k, v in rel.properties.items():
                if isinstance(v, str):
                    v = str(v).replace("'", "\\'")
                props_list.append(f"{k}: '{v}'")

            props_str = f" {{{', '.join(props_list)}}}" if props_list else ""

            from_canonical = resolve_entity_name(rel.from_node).replace("'", "\\'")
            to_canonical = resolve_entity_name(rel.to_node).replace("'", "\\'")

            queries.append(
                f"MATCH (a {{name: '{from_canonical}'}}), (b {{name: '{to_canonical}'}}) "
                f"MERGE (a)-[:{rel.type}{props_str}]->(b)"
            )

        return queries
