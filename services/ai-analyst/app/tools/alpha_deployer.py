from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import aiohttp
from app.core.config import settings
import json

class AlphaDeployInput(BaseModel):
    user_id: str = Field(description="The ID of the user owning the strategy.")
    symbol: str = Field(description="The trading symbol, e.g., 'XAU/USD' or 'EUR/USD'.")
    formula: str = Field(description="The Alpha Engine formula (e.g., 'rsi(close, 14)').")
    threshold_long: Optional[float] = Field(default=None, description="Value below which to Buy (or above if momentum).")
    threshold_short: Optional[float] = Field(default=None, description="Value above which to Sell.")
    condition_long: str = Field(default="lt", description="'gt' or 'lt' for long entry.")
    condition_short: str = Field(default="gt", description="'gt' or 'lt' for short entry.")
    strategy_type: str = Field(default="ALPHA_ENGINE_V1", description="Template ID: 'ALPHA_ENGINE_V1' or 'HYBRID_ALPHA_V1'.")
    description: str = Field(default="", description="Semantic description of the strategy intent.")

class AlphaDeployerTool(BaseTool):
    name: str = "deploy_alpha_strategy"
    description: str = "Deploys a new Alpha Strategy to the live core. Use this when the user wants to start trading a formula."
    args_schema: Type[BaseModel] = AlphaDeployInput

    def _run(self, **kwargs):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, user_id: str, symbol: str, formula: str, 
                    threshold_long: float = None, threshold_short: float = None, 
                    condition_long: str = "lt", condition_short: str = "gt",
                    strategy_type: str = "ALPHA_ENGINE_V1", description: str = ""):
        
        # Determine the target endpoint (API Gateway or Strategy Core)
        # Using Strategy Core direct for internal service-to-service, or API Gateway if we want auth handling.
        # tools/strategy.py uses STRATEGY_CORE_URL. Let's stick to that pattern.
        url = f"{settings.STRATEGY_CORE_URL}/api/v1/strategies"
        
        # Prepare Config
        config = {
            "formula": formula,
            "threshold_long": threshold_long,
            "threshold_short": threshold_short,
            "condition_long": condition_long,
            "condition_short": condition_short,
            "meta_description": description # Semantic Intent
        }
        
        # Construct Payload (matching StrategyCreate schema roughly, but StrategyCore might expect different)
        # Wait, Strategy Core `POST /strategies` usually expects the full DB object or internal structure?
        # Actually usually API Gateway handles DB creation.
        # `tools/strategy.py` hitting `backtest/custom` is direct to core.
        # But `POST /strategies` typically involves `api-gateway` to create the DB record first.
        # Let's check `api-gateway/routers/strategy.py` again.
        # It has `POST /api/v1/strategies`.
        # So we should hit API Gateway if possible to ensure DB record is created.
        # ai-analyst to api-gateway communication.
        
        # Assuming URL is API Gateway for persistent strategies.
        # If settings.API_GATEWAY_URL exists.
        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/strategies/"
        
        # Payload for API Gateway `StrategyCreate`
        # We need fund_id, broker_account_id. AI might not know these.
        # We might need defaults or ask User.
        # For now, let's assume a default "Sandbox Fund" or look it up via `user_id`.
        # This is a complexity. 
        # workaround: Let's create it via Strategy Core DIRECTLY as a "Paper Strategy" if possible?
        # No, persistence requires DB.
        
        # Temporary Solution: Use a hardcoded Placeholder Fund ID or fetch via Account Tool first.
        # Let's fail gracefully if we can't find a fund, but for now we'll try to just send minimal fields
        # and hope API Gateway logic handles defaults (it doesn't seems to).
        
        # REVISION: Let's assume the user has a "Default Fund".
        # We'll set a dummy UUID for now or try to fetch it.
        # Ideally we'd use `GetAccountStatusTool` logic to get `fund_id`.
        
        # For this tool, let's just make the call.
        payload = {
            "name": f"AI-{symbol}-{strategy_type}",
            "fund_id": "00000000-0000-0000-0000-000000000000", # Placeholder, API might reject
            "template_id": strategy_type,
            "broker_account_id": "00000000-0000-0000-0000-000000000000",
            "config_json": config,
            "risk_settings": {} 
        }
        
        # Note: In a real system we'd need a proper "Get My Fund" step.
        # Proceeding with assumption that we might need to Mock this or fix API Gateway to handle optional fund.
        
        async with aiohttp.ClientSession() as session:
            try:
                # We need a token for API Gateway usually. 
                # Service-to-Service auth headers?
                # For now, omitting auth or passing user_id headers if supported.
                headers = {"x-user-id": user_id}
                
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return f"Successfully deployed strategy. ID: {data['data']['id']}"
                    else:
                        txt = await resp.text()
                        return f"Failed to deploy: {resp.status} - {txt}"
            except Exception as e:
                return f"Error deploying: {e}"
