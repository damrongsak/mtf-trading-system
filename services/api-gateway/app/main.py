from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import risk, signal, backtest

app = FastAPI(title="MTF Trading System API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(risk.router, prefix="/api/v1/risk")
app.include_router(signal.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
