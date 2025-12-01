from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import signal, risk, auth, backtest, strategy, journal

app = FastAPI(
    title="MTF Trading System API",
    description="API Gateway for Signal Generation, Risk Management, and AI Analysis",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(signal.router)
app.include_router(risk.router)
app.include_router(strategy.router)
app.include_router(journal.router)
app.include_router(backtest.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok"}
