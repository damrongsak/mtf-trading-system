from fastapi import APIRouter
from pydantic_models import SignalRequest, SignalResponse

router = APIRouter()


@router.post("/check")
async def check_signal(req: SignalRequest) -> SignalResponse:
    # Contract-first: implement logic to call strategy-core service
    return SignalResponse(allowed=False, reason="not implemented")
