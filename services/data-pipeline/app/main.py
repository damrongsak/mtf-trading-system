from fastapi import FastAPI
from app.routes import router

app = FastAPI(title="Data Pipeline Service")

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "data-pipeline"}
