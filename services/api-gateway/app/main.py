import os
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.logging_config import setup_logging

# Configure logging
logger = setup_logging()
from app.routers import signal, signals, risk, backtest, strategy, saved_strategies, journal, auth, dashboard, fund, settings, transaction, simulation, ai, data, execution, stream, market, analysis, market_data, broker_account, system, deployments, internal, foundry, features, olympus, external, api_key, analytics, orchestration, alerts
from app.routers import indicators as indicators_router_module

from app.schemas.response import ErrorCode
from app.utils.response import error_response
from app.streaming.manager import stream_manager
from app.database import SessionLocal

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

    # Start Telegram Long Polling (if enabled)
    polling_enabled = os.getenv("TELEGRAM_POLLING_ENABLED", "false").lower() == "true"
    if polling_enabled:
        try:
            from app.services.telegram_polling import TelegramPollingService
            app.state.telegram_polling = TelegramPollingService(
                db_session_factory=SessionLocal
            )
            await app.state.telegram_polling.start()
        except Exception as e:
            logger.error(f"Failed to start Telegram polling: {e}")
    else:
        app.state.telegram_polling = None

@app.on_event("shutdown")
async def shutdown_event():
    await stream_manager.stop()
    if getattr(app.state, "telegram_polling", None):
        await app.state.telegram_polling.stop()

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_code_map = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        503: ErrorCode.SERVICE_UNAVAILABLE,
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
# Single Source of Truth: /specs/04_api_spec.yaml (Docker) or ../../specs/04_api_spec.yaml (Local)
SPEC_LOCATIONS = [
    "/specs/04_api_spec.yaml",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "specs", "04_api_spec.yaml")),
    os.path.abspath(os.path.join(os.getcwd(), "specs", "04_api_spec.yaml")),
    "specs/04_api_spec.yaml"
]

for spec_path in SPEC_LOCATIONS:
    if os.path.exists(spec_path):
        logger.info(f"Loading OpenAPI spec from {spec_path}")
        with open(spec_path, "r") as f:
            app.openapi_schema = yaml.safe_load(f)
        break
else:
    logger.warning("No OpenAPI spec found in search locations. Using default schema generation.")

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

from app.middleware import RequestIDMiddleware
app.add_middleware(RequestIDMiddleware)

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
app.include_router(signals.router)
app.include_router(risk.router)
app.include_router(strategy.router)
app.include_router(journal.router)
app.include_router(transaction.router)
app.include_router(simulation.router)
app.include_router(ai.router)
app.include_router(olympus.router)
app.include_router(analytics.router, prefix="/api/v1")

# Routers with prefixes (matching Nginx rewrites or specific paths)
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(data.router) # prefix in router (/api/v1/data)
app.include_router(features.router, prefix="/api/v1/data")
app.include_router(broker_account.router)
app.include_router(market.router, prefix="/api/v1/market")
app.include_router(stream.router, prefix="/api/v1/stream")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
# app.include_router(saved_strategies.router, prefix="/api/v1") # REMOVED: Merged into strategy.router to avoid prefix clash
app.include_router(deployments.router, prefix="/api/v1/deployments")
app.include_router(internal.router)
app.include_router(foundry.router, prefix="/api/v1")

from app.routers import plugins, alpha, telegram, news, data_source, analysis, prompts, knowledge

app.include_router(plugins.router, prefix="/api/v1")
app.include_router(alpha.router, prefix="/api/v1")
app.include_router(telegram.router, prefix="/api/v1")
app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(data_source.router, prefix="/api/v1", tags=["Data Sources"])
app.include_router(backtest.router, prefix="/api/v1", tags=["Backtest"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["Prompts"])
app.include_router(knowledge.router)
app.include_router(news.router)
app.include_router(external.router, prefix="/api/v1", tags=["3rd Party Gateway"])
app.include_router(api_key.router, prefix="/api/v1", tags=["API Key Management"])
app.include_router(orchestration.router)
app.include_router(indicators_router_module.router)  # POST /api/v1/indicators

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok"}
