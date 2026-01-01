from fastapi import APIRouter, HTTPException
from app.schemas import FoundryAssembleRequest, FoundryAssembleResponse, WalkForwardRequest, WalkForwardResponse
from app.foundry.factory import StrategyAssembler
from app.proving_ground.validator import WalkForwardValidator
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

@router.post("/validate", response_model=WalkForwardResponse)
def validate_strategy(req: WalkForwardRequest):
    try:
        # Fetch Data
        from app.backtest import fetch_data_from_db
        from app.database import SessionLocal
        from app.utils.helpers import resolve_market_symbol_id
        
        db = SessionLocal()
        try:
            ms_id = resolve_market_symbol_id(db, req.symbol)
            if not ms_id:
                raise HTTPException(status_code=404, detail=f"MarketSymbol not found for {req.symbol}")
        finally:
            db.close()

        df = fetch_data_from_db(
            market_symbol_id=ms_id,
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date
        )
        
        if df.empty:
             raise HTTPException(status_code=400, detail="No data found")
             
        # Run WFA
        validator = WalkForwardValidator(req.config, df)
        result = validator.run()
        
        return WalkForwardResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
