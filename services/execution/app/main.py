from fastapi import FastAPI, HTTPException
from app.executor import can_execute, ExecutionRequest, ExecutionResult

app = FastAPI(title="Execution Service")

@app.post("/check", response_model=ExecutionResult)
async def check_risk(req: ExecutionRequest):
    try:
        result = can_execute(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
