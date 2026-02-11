from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from app.utils.response import success_response
import base64

router = APIRouter()

@router.post("/upload")
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
