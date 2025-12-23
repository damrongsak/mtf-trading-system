
class LogicTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    default_config: dict
    default_risk_settings: dict

@router.get("/templates", response_model=APIResponse[List[LogicTemplateResponse]])
def list_templates():
    # Mock data for now - typically fetching from Strategy Core Registry
    templates = [
        LogicTemplateResponse(
            id="SMC_V1",
            name="Smart Money Concepts V1",
            description="Order Block + FVG strategy with MTF analysis",
            default_config={
                "timeframes": ["15m", "1h", "4h"],
                "risk_per_trade": 1.0,
                "rr_ratio": 2.0
            },
            default_risk_settings={
                "max_drawdown": 5.0,
                "daily_loss_limit": 2.0
            }
        ),
        LogicTemplateResponse(
            id="MACD_CROSS_V1",
            name="MACD Crossover",
            description="Classic MACD crossover strategy",
            default_config={
                "fast": 12,
                "slow": 26,
                "signal": 9
            },
            default_risk_settings={
                 "max_drawdown": 10.0
            }
        )
    ]
    return success_response(data=templates)
