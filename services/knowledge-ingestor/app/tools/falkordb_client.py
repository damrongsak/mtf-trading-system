import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import redis


class FalkorDBClient:
    """
    Optimized client for interacting with FalkorDB.
    Uses class-level connection pooling to share Redis clients across instances.
    """

    _connection_pool: Dict[str, "redis.Redis"] = {}

    def __init__(
        self,
        host: str = "falkordb",
        port: int = 6379,
        graph_name: str = "OlympusKnowledgeGraph",
    ):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self._client: Optional["redis.Redis"] = None

    def connect(self) -> Dict[str, Any]:
        """Establish connection to FalkorDB using shared pool"""
        pool_key = f"{self.host}:{self.port}"

        if pool_key in FalkorDBClient._connection_pool:
            self._client = FalkorDBClient._connection_pool[pool_key]
            try:
                self._client.ping()
                return {"status": "connected", "pooled": True, "graph": self.graph_name}
            except Exception:
                # Pool instance failed, recreate
                del FalkorDBClient._connection_pool[pool_key]

        try:
            import redis

            self._client = redis.Redis(
                host=self.host, port=self.port, decode_responses=True, socket_timeout=10
            )
            self._client.ping()
            FalkorDBClient._connection_pool[pool_key] = self._client
            return {"status": "connected", "pooled": False, "graph": self.graph_name}
        except ImportError:
            return {"status": "error", "message": "redis module not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def execute_query(self, cypher: str) -> Dict[str, Any]:
        """Execute a single Cypher query"""
        if not self._client:
            self.connect()
        if not self._client:
            return {"status": "error", "message": "Not connected"}

        try:
            result = self._client.execute_command(
                "GRAPH.QUERY", self.graph_name, cypher
            )
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "query": cypher[:100]}

    def execute_batch(self, queries: List[str], chunk_size: int = 50) -> Dict[str, Any]:
        """
        Execute multiple queries using Redis pipelining for performance.
        Splits giant batches into smaller chunks.
        """
        if not self._client:
            self.connect()
        if not self._client:
            return {"status": "error", "message": "Not connected"}

        valid_queries = [q.strip() for q in queries if q.strip()]
        if not valid_queries:
            return {"total": 0, "success": 0, "failed": 0, "results": []}

        success_count = 0
        failed_count = 0
        all_results = []

        # Process in chunks to avoid blocking
        for i in range(0, len(valid_queries), chunk_size):
            chunk = valid_queries[i : i + chunk_size]
            pipeline = self._client.pipeline(transaction=False)

            for q in chunk:
                pipeline.execute_command("GRAPH.QUERY", self.graph_name, q)

            try:
                chunk_results = pipeline.execute(raise_on_error=False)
                for q, res in zip(chunk, chunk_results):
                    if isinstance(res, Exception):
                        failed_count += 1
                        all_results.append(
                            {"status": "error", "query": q[:50], "message": str(res)}
                        )
                    else:
                        success_count += 1
                        all_results.append({"status": "success", "query": q[:50]})
            except Exception as e:
                failed_count += len(chunk)
                all_results.append({"status": "batch_error", "message": str(e)})

        return {
            "total": len(valid_queries),
            "success": success_count,
            "failed": failed_count,
            "results": all_results[:100],  # Cap detailed results
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        if not self._client:
            self.connect()
        if not self._client:
            return {"status": "error", "message": "Not connected"}
        try:
            result = self._client.execute_command("GRAPH.INFO", self.graph_name)
            return {"status": "success", "info": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_content_exists(self, content_hash: str) -> bool:
        """Check if a node with this hash already exists in the graph"""
        if not self._client:
            self.connect()
        if not self._client:
            return False

        query = f"MATCH (p:Paper {{hash: '{content_hash}'}}) RETURN p.title LIMIT 1"
        try:
            result = self._client.execute_command("GRAPH.QUERY", self.graph_name, query)
            # result[0] contains the header, result[1] contains rows
            if isinstance(result, list) and len(result) > 1 and result[1]:
                return True
            return False
        except Exception as e:
            print(f"Error checking hash existence: {e}")
            return False

    def delete_graph(self) -> Dict[str, Any]:
        """Delete the entire graph"""
        if not self._client:
            self.connect()
        if not self._client:
            return {"status": "error", "message": "Not connected"}
        try:
            # Note: GRAPH.DELETE returns 'OK' or error
            result = self._client.execute_command("GRAPH.DELETE", self.graph_name)
            return {"status": "success", "result": result}
        except Exception as e:
            if "Graph not found" in str(e):
                return {"status": "success", "message": "Graph already empty"}
            return {"status": "error", "message": str(e)}

    def delete_by_hash(self, content_hash: str) -> Dict[str, Any]:
        """
        Delete nodes/edges associated with a specific document hash.
        This is a 'soft' deletion of the document's footprint.
        We find nodes connected to the Paper node and delete relationships.
        """
        if not self._client:
            self.connect()
        if not self._client:
            return {"status": "error", "message": "Not connected"}

        # 1. Find the filename associated with the hash
        find_query = f"MATCH (p:Paper {{hash: '{content_hash}'}}) RETURN p.name"
        try:
            res = self.execute_query(find_query)
            if not res.get("result") or not isinstance(res["result"], list) or len(res["result"]) < 2 or not res["result"][1]:
                return {"status": "success", "message": "No data found for this hash"}

            filename = res["result"][1][0][0]

            # 2. Delete all relationships with this source_ref
            rel_query = f"MATCH ()-[r]->() WHERE r.source_ref = '{filename}' DELETE r"
            self.execute_query(rel_query)

            # 3. Delete the Paper node itself
            paper_query = f"MATCH (p:Paper {{hash: '{content_hash}'}}) DELETE p"
            self.execute_query(paper_query)

            return {
                "status": "success",
                "message": f"Deleted document footprint for {filename}",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Tool functions for OpenClaw
def falkordb_connect(
    host: str = "falkordb", port: int = 6379, graph: str = "OlympusKnowledgeGraph"
) -> str:
    """Connect to FalkorDB"""
    client = FalkorDBClient(host, port, graph)
    return json.dumps(client.connect(), indent=2)


def falkordb_query(
    cypher: str,
    host: str = "falkordb",
    port: int = 6379,
    graph: str = "OlympusKnowledgeGraph",
) -> str:
    """Execute a Cypher query"""
    client = FalkorDBClient(host, port, graph)
    client.connect()
    return json.dumps(client.execute_query(cypher), indent=2)


def falkordb_batch(
    queries: List[str],
    host: str = "falkordb",
    port: int = 6379,
    graph: str = "OlympusKnowledgeGraph",
) -> str:
    """Execute multiple Cypher queries"""
    client = FalkorDBClient(host, port, graph)
    client.connect()
    return json.dumps(client.execute_batch(queries), indent=2)


if __name__ == "__main__":
    # Quick test
    client = FalkorDBClient()
    print("Testing connection...")
    print(json.dumps(client.connect(), indent=2))
