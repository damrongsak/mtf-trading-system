from fastapi import APIRouter, HTTPException, Depends
from app.services.rag import RAGService
from app.utils.response import success_response

router = APIRouter()
rag_service = RAGService()

@router.get("/qdrant/health")
async def get_qdrant_health():
    """
    Get detailed telemetry of Qdrant collections.
    """
    try:
        collections = [
            rag_service.journal_collection,
            rag_service.strategy_collection,
            rag_service.docs_collection,
            rag_service.library_collection
        ]
        
        stats = {}
        for col in collections:
            stats[col] = rag_service.get_collection_stats(col)
            
        return success_response(
            data={
                "collections": stats,
                "overall_status": "HEALTHY" if all(c.get("status") == "green" for c in stats.values() if "error" not in c) else "DEGRADED"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.post("/qdrant/collections/{collection_name}/clear")
async def clear_collection(collection_name: str):
    """
    Wipe a collection and recreate it. Dangerous Admin operation.
    """
    try:
        rag_service.clear_collection(collection_name)
        return success_response(
            message=f"Collection '{collection_name}' has been cleared and reset."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear operation failed: {str(e)}")
