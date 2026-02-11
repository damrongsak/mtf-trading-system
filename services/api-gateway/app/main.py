import os
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.logging_config import setup_logging

# Configure logging
logger = setup_logging()
from app.routers import signal, risk, backtest, strategy, saved_strategies, journal, auth, dashboard, fund, settings, transaction, simulation, ai, data, execution, stream, market, analysis, market_data, broker_account, system, deployments, internal, foundry
# ... (existing code)
from app.schemas.response import ErrorCode
from app.utils.response import error_response
from app.streaming.manager import stream_manager

app = FastAPI(
    title="MTF Trading System API",
    description="API Gateway for Signal Generation, Risk Management, and AI Analysis",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    await stream_manager.start()
    
    # Start Scheduler
    try:
        from app.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"Failed to start scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await stream_manager.stop()

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
SPEC_PATH = "../../specs/04_api_spec.yaml"
if os.path.exists(SPEC_PATH):
    with open(SPEC_PATH, "r") as f:
        app.openapi_schema = yaml.safe_load(f)

# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if not os.path.exists(static_path):
    os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(fund.router)
app.include_router(settings.router)
app.include_router(signal.router)
app.include_router(risk.router)
app.include_router(strategy.router)
app.include_router(journal.router)
app.include_router(transaction.router)
app.include_router(simulation.router)
app.include_router(ai.router)

# Routers with prefixes (matching Nginx rewrites or specific paths)
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(data.router) # data router likely has /api/v1/data inside or is handled
app.include_router(stream.router, prefix="/api/v1/stream")
app.include_router(market.router, prefix="/api/v1/market")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(broker_account.router)
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
app.include_router(saved_strategies.router, prefix="/api/v1")
app.include_router(deployments.router, prefix="/api/v1/deployments")
app.include_router(internal.router)
app.include_router(foundry.router, prefix="/api/v1")
from app.routers import plugins
app.include_router(plugins.router, prefix="/api/v1")
from app.routers import alpha
app.include_router(alpha.router, prefix="/api/v1")
from app.routers import telegram
app.include_router(telegram.router, prefix="/api/v1")

from app.routers import auth, strategy, execution, risk, data_source, backtest, journal, data, analysis, prompts, ai

# execution router already has /execution prefix
app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
app.include_router(data_source.router, prefix="/api/v1", tags=["Data Sources"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["Backtest"])
# data router has its own prefix /api/v1/data
app.include_router(data.router)
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["Prompts"])

from app.routers import news
app.include_router(news.router)



@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok"}
