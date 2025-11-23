from fastapi import FastAPI
from app.routers import signal, backtest, risk

app = FastAPI(title="MTF Trading API")
app.include_router(signal.router, prefix="/api/v1/signal")
app.include_router(backtest.router, prefix="/api/v1/backtest")
app.include_router(risk.router, prefix="/api/v1/risk")


@app.get("/health")
async def health():
    return {"status": "ok"}
