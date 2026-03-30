from app.tools.falkordb_client import FalkorDBClient
from app.core.app_config import config


def run_analysis():
    client = FalkorDBClient(config.falkor_host, config.falkor_port, config.graph_name)
    client.connect()

    print("=" * 60)
    print("      OLYMPUS KNOWLEDGE GRAPH - INTELLIGENCE REPORT")
    print("=" * 60)

    # 1. Macro-to-Asset Impact Chains
    print("\n🔍 CAUSAL IMPACT CHAINS (Macro -> Asset):")
    query = """
    MATCH (m:MacroIndicator)-[r]->(a:Asset)
    RETURN m.name as indicator, type(r) as impact, a.name as asset
    LIMIT 15
    """
    res = client.execute_query(query)
    data = res.get("result", [])
    if len(data) > 1 and data[1]:
        rows = data[1]
        for row in rows:
            print(f" • {row[0]} --[{row[1]}]--> {row[2]}")
    else:
        print(" • No direct causal chains found yet.")

    # 2. Key Strategies & Their Context
    print("\n📈 TRADING STRATEGIES & MARKET CONTEXT:")
    query = """
    MATCH (s:Strategy)
    OPTIONAL MATCH (s)-[:MENTIONS|PROPOSES_STRATEGY]->(target)
    RETURN s.name, labels(target)[0] as type, target.name as target_name
    LIMIT 10
    """
    res = client.execute_query(query)
    data = res.get("result", [])
    if len(data) > 1 and data[1]:
        rows = data[1]
        for row in rows:
            ctx = f"({row[1]}: {row[2]})" if row[1] else "No context"
            print(f" • Strategy: {row[0]} | Context: {ctx}")
    else:
        print(" • No explicit strategies found.")

    # 3. Market Centrality (The 'Hub' Entities)
    print("\n🏗️ CORE THEMES & CENTRAL HUB NODES (Connectivity > 3):")
    query = """
    MATCH (n)
    WITH n, size((n)--()) as degree
    WHERE degree > 3 AND n.name IS NOT NULL
    RETURN labels(n)[0] as label, n.name as name, degree
    ORDER BY degree DESC
    LIMIT 12
    """
    res = client.execute_query(query)
    data = res.get("result", [])
    if len(data) > 1 and data[1]:
        rows = data[1]
        for row in rows:
            print(f" • [{row[0]}] {row[1]} (Connections: {row[2]})")

    # 4. Global Stats
    print("\n📊 GRAPH MAGNITUDE:")
    query = "MATCH (n) RETURN count(n)"
    res = client.execute_query(query)
    print(f" • Total Nodes: {res.get('result', [[''], [[0]]])[1][0][0]}")


if __name__ == "__main__":
    run_analysis()
