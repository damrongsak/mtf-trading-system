from fastapi import APIRouter, HTTPException
from app.schemas import FoundryAssembleRequest, FoundryAssembleResponse
from app.foundry.factory import StrategyAssembler
import hashlib
import json

router = APIRouter(prefix="/foundry", tags=["foundry"])

@router.post("/assemble", response_model=FoundryAssembleResponse)
def assemble_strategy(req: FoundryAssembleRequest):
    try:
        # Validate that we can assemble the pipeline
        pipeline = StrategyAssembler.assemble(req.config)
        
        # Calculate hash of the config as ID
        config_str = json.dumps(req.config, sort_keys=True)
        pipeline_hash = hashlib.sha256(config_str.encode()).hexdigest()
        
        return FoundryAssembleResponse(
            pipeline_hash=pipeline_hash,
            errors=[]
        )
    except Exception as e:
        return FoundryAssembleResponse(
            pipeline_hash="",
            errors=[str(e)]
        )
