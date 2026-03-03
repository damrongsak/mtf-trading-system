from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional, List
from app.services.rag import RAGService
from app.utils.response import success_response, error_response
from app.database import SessionLocal
from app.models.rag import LibraryBook, IngestionStatus
import base64
import asyncio

router = APIRouter()
rag_service = RAGService()

@router.post("/ingest/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    context_type: str = Form("strategy_context") # strategy_context, market_context
):
    """
    Upload a file (PDF, Image, Markdown) to be used as context for AI Agents.
    Returns a base64 string or stored path reference that can be passed to Agents.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        content = await file.read()
        
        # Determine mime type
        mime_type = file.content_type
        filename = file.filename
        
        # For simplicity in this phase, we convert to base64 immediately for direct Gemini injection.
        # In prod, we might store to GCS/S3 and pass URI.
        b64_content = base64.b64encode(content).decode("utf-8")
        
        return success_response(
            data={
                "filename": filename,
                "mime_type": mime_type,
                "size": len(content),
                "context_ref": {
                    "type": "base64",
                    "data": b64_content,
                    "mime_type": mime_type
                }
            },
            message="File uploaded successfully. Pass 'context_ref' to Agent chat."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/library/ingest")
async def ingest_library_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    collection: Optional[str] = Form(None)
):
    """
    Upload and semantically ingest a book into the specialized quant_library collection.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        content = await file.read()
        text_content = content.decode("utf-8", errors="ignore")
        
        filename = file.filename
        metadata = {}
        if title: metadata["title"] = title
        if author: metadata["author"] = author

        # Run ingestion in background to avoid blocking the request
        asyncio.create_task(rag_service.ingest_library_book(
            filename=filename,
            content=text_content,
            metadata=metadata,
            collection=collection
        ))

        return success_response(
            data={
                "filename": filename,
                "collection": collection or "quant_library",
                "status": "INGESTION_STARTED",
                "message": "The book is being processed in the background."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion initiation failed: {str(e)}")

@router.get("/library/status/{filename}")
async def get_library_ingestion_status(filename: str):
    """
    Get the ingestion status of a library book by filename.
    """
    db = SessionLocal()
    try:
        book = db.query(LibraryBook).filter(LibraryBook.filename == filename).first()
        if not book:
            return error_response(
                message=f"Book with filename '{filename}' not found",
                status_code=404
            )
        
        return success_response(
            data={
                "filename": book.filename,
                "title": book.title,
                "author": book.author,
                "status": book.ingestion_status.value,
                "total_chunks": book.total_chunks,
                "last_ingested_at": book.last_ingested_at
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/library/list")
async def list_library_books():
    """
    List all books in the library with their ingestion status.
    """
    db = SessionLocal()
    try:
        books = db.query(LibraryBook).all()
        return success_response(
            data=[{
                "id": str(book.id),
                "filename": book.filename,
                "title": book.title,
                "author": book.author,
                "status": book.ingestion_status.value,
                "last_ingested_at": book.last_ingested_at
            } for book in books]
        )
    finally:
        db.close()
