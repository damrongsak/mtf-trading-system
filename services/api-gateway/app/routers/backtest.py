from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_backtests():
    return {"message": "Backtest router placeholder"}
