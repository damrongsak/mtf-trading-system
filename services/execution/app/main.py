from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.executor import can_execute, ExecutionRequest, ExecutionResult

app = FastAPI(title="Execution Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
