from fastapi import APIRouter, UploadFile, File, Query, HTTPException, status
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os

router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
    responses={404: {"description": "Not found"}},
)

DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_historical_data(
    file: UploadFile = File(...),
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)")
):
    """
    Upload historical OHLCV data via CSV.
    Proxies the request to the Data Pipeline service.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    async with httpx.AsyncClient() as client:
        try:
            # Read file content
            content = await file.read()
            
            # Prepare multipart upload
            files = {
                'file': (file.filename, content, file.content_type or 'text/csv')
            }
            params = {
                'symbol': symbol,
                'timeframe': timeframe
            }
            
            # Forward to Data Pipeline
            # Note: Internal service path is /api/v1/upload
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/upload",
                params=params,
                files=files,
                timeout=30.0 # Allow more time for large uploads
            )
            
            if response.status_code != 201:
                # Propagate error details
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            return response.json()

        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    symbol: str = Query(..., description="Symbol to sync (e.g. XAU_USD)")
):
    """
    Trigger manual data sync for a symbol.
    Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/ingest/manual",
                params={"symbol": symbol},
                timeout=10.0
            )
            
            if response.status_code not in [200, 202]:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
