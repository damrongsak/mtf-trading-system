import os
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routers import signal, risk, backtest, strategy, journal, auth, dashboard, fund, settings, transaction, simulation, ai, data
from app.schemas.response import ErrorCode
from app.utils.response import error_response

app = FastAPI(
    title="MTF Trading System API",
    description="API Gateway for Signal Generation, Risk Management, and AI Analysis",
    version="0.1.0"
)

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_code_map = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.detail,
            error_code=error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal Server Error",
            error_code=ErrorCode.INTERNAL_ERROR
        )
    )

# Attempt to load OpenAPI spec from file (SDD)
# This path works for local dev when running from services/api-gateway
# In Docker, you would need to mount/copy the spec file.
SPEC_PATH = "../../specs/02_api_spec.yaml"
if os.path.exists(SPEC_PATH):
    with open(SPEC_PATH, "r") as f:
        app.openapi_schema = yaml.safe_load(f)

# CORS Middleware
# Explicitly allow all origins for development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(fund.router)
app.include_router(settings.router)
app.include_router(signal.router)
app.include_router(risk.router)
app.include_router(strategy.router)
app.include_router(journal.router)
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(transaction.router)
app.include_router(simulation.router)
app.include_router(ai.router)
app.include_router(data.router)



@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok"}
