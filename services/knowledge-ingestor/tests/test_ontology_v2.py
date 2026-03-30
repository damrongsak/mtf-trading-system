from app.core.ontology import (
    GraphExtractionSchema,
    NodeSchema,
    RelationshipSchema,
    resolve_entity_name,
)


def test_entity_resolution_synonyms():
    """Verify common financial synonyms are resolved to canonical names."""
    assert resolve_entity_name("Fed") == "Federal Reserve"
    assert resolve_entity_name("XAU") == "Gold"
    assert resolve_entity_name("XAUUSD") == "Gold"
    assert resolve_entity_name("BTC") == "Bitcoin"
    assert resolve_entity_name("US") == "United States"
    assert resolve_entity_name("unknown_asset") == "unknown_asset"


def test_to_cypher_node_generation():
    """Verify nodes are created with canonical names and labels."""
    node = NodeSchema(label="Asset", name="XAU", properties={"type": "COMMODITY"})
    schema = GraphExtractionSchema(
        thought_process="Test thought", nodes=[node], relationships=[]
    )

    queries = schema.to_cypher()
    assert len(queries) == 1
    # Check if name was resolved to "Gold"
    assert "name: 'Gold'" in queries[0]
    assert "Asset" in queries[0]
    assert "type: 'COMMODITY'" in queries[0]


def test_to_cypher_relationship_no_cartesian():
    """Verify relationships use MATCH before MERGE (specific matching)."""
    node_a = NodeSchema(label="Asset", name="Fed")
    node_b = NodeSchema(label="MacroIndicator", name="Inflation")
    rel = RelationshipSchema(from_node="Fed", to_node="Inflation", type="INFLUENCES")

    schema = GraphExtractionSchema(
        thought_process="Test thought", nodes=[node_a, node_b], relationships=[rel]
    )
    queries = schema.to_cypher()

    # 2 nodes + 1 relationship
    assert len(queries) == 3

    rel_query = queries[2]
    # Check for non-Cartesian MATCH logic
    assert "MATCH (a {name: 'Federal Reserve'}), (b {name: 'Inflation'})" in rel_query
    assert "MERGE (a)-[:INFLUENCES" in rel_query


def test_to_cypher_property_escaping():
    """Verify single quotes in names/properties are escaped."""
    node = NodeSchema(
        label="Organization",
        name="Bank of England",
        properties={"comment": "It's a test"},
    )
    schema = GraphExtractionSchema(
        thought_process="Test thought", nodes=[node], relationships=[]
    )

    queries = schema.to_cypher()
    assert "It\\'s a test" in queries[0]
