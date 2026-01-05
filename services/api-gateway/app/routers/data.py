from fastapi import APIRouter, UploadFile, File, Query, HTTPException, status
from app.schemas.response import APIResponse
from app.utils.response import success_response, error_response
import httpx
from typing import Optional
from datetime import datetime
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

@router.post("/open-interest/upload", status_code=status.HTTP_201_CREATED)
async def upload_open_interest(
    file: UploadFile = File(...),
    snapshot_at: Optional[datetime] = None
):
    """
    Upload Open Interest Matrix Excel file.
    Proxies to Data Pipeline.
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx).")

    async with httpx.AsyncClient() as client:
        try:
            content = await file.read()
            files = {'file': (file.filename, content, file.content_type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            params = {}
            if snapshot_at:
                params['snapshot_at'] = snapshot_at.isoformat()

            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest",
                params=params,
                files=files,
                timeout=60.0
            )

            if response.status_code != 201:
                 # Propagate error
                 try:
                     err = response.json()
                     detail = err.get('detail', response.text)
                 except:
                     detail = response.text
                 raise HTTPException(status_code=response.status_code, detail=detail)

            return response.json()

        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.get("/open-interest/snapshots")
async def get_open_interest_snapshots(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get available OI snapshots. Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest/snapshots",
                params={"limit": limit},
                timeout=5.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/details")
async def get_open_interest_details(
    snapshot_at: datetime = Query(...),
    contract: Optional[str] = Query(None),
    min_oi: int = Query(0),
    max_oi: Optional[int] = Query(None),
    smart_filter: bool = Query(True)
):
    """
    Get detailed OI records. Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "snapshot_at": snapshot_at.isoformat(),
                "min_oi": min_oi,
                "smart_filter": str(smart_filter).lower()
            }
            if contract:
                params["contract"] = contract
            if max_oi is not None:
                params["max_oi"] = max_oi

            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest/details",
                params=params,
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/analysis")
async def get_open_interest_analysis(
    snapshot_at: datetime = Query(...),
    contract: Optional[str] = Query(None),
    min_oi: int = Query(0),
    max_oi: Optional[int] = Query(None)
):
    """
    Get detailed OI analysis. Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "snapshot_at": snapshot_at.isoformat(),
                "min_oi": min_oi
            }
            if contract:
                params["contract"] = contract
            if max_oi is not None:
                params["max_oi"] = max_oi

            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest/analysis",
                params=params,
                timeout=10.0
            )
            if response.status_code != 200:
                # If pipeline returns 404/500, propagate
                # Ideally, we should check application/json vs text
                try:
                    detail = response.json().get('detail', response.text)
                except:
                    detail = response.text
                raise HTTPException(status_code=response.status_code, detail=detail)

            return response.json()
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/contracts")
async def get_open_interest_contracts(
    snapshot_at: datetime = Query(...)
):
    """
    Get list of contracts. Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest/contracts",
                params={"snapshot_at": snapshot_at.isoformat()},
                timeout=5.0
            )
            if response.status_code != 200:
                 try:
                    detail = response.json().get('detail', response.text)
                 except:
                    detail = response.text
                 raise HTTPException(status_code=response.status_code, detail=detail)
            return response.json()
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

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
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)"),
    broker: str = Query("OANDA", description="Data Provider (e.g. OANDA, BINANCE)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """
    Get candles from Data Pipeline. Proxy endpoint.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "symbol": symbol,
                "timeframe": timeframe,
                "broker": broker,
                "page": page,
                "page_size": page_size
            }
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/candles",
                params=params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            return response.json()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/symbols")
async def get_active_symbols(
    broker: str = Query("OANDA", description="Filter by broker name")
):
    """
    Get list of active symbols for a specific broker.
    Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/symbols",
                params={"broker": broker},
                timeout=5.0
            )
            
            if response.status_code != 200:
                # If pipeline returns 404/500, propagate
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.patch("/symbols/{symbol_id}")
async def update_symbol_status(
    symbol_id: str,
    payload: dict,
):
    """
    Update symbol status. Proxies to Data Pipeline.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{DATA_SERVICE_URL}/api/v1/symbols/{symbol_id}",
                json=payload,
                timeout=5.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
