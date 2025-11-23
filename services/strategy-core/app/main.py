from fastapi import FastAPI

app = FastAPI(title="Strategy Core Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "strategy-core"}
