import logging
from typing import Type, Optional, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import aiohttp
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

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

    def _run(self, **kwargs) -> str:
        import asyncio
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, user_id: str, symbol: str, formula: str, 
                    threshold_long: Optional[float] = None, 
                    threshold_short: Optional[float] = None, 
                    condition_long: str = "lt", 
                    condition_short: str = "gt",
                    strategy_type: str = "ALPHA_ENGINE_V1", 
                    description: str = "", **kwargs) -> str:
        
        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/strategies/"
        
        # Prepare Config
        config = {
            "formula": formula,
            "threshold_long": threshold_long,
            "threshold_short": threshold_short,
            "condition_long": condition_long,
            "condition_short": condition_short,
            "meta_description": description
        }
        
        payload = {
            "name": f"AI-{symbol}-{strategy_type}",
            "fund_id": "00000000-0000-0000-0000-000000000000", # Placeholder
            "template_id": strategy_type,
            "broker_account_id": "00000000-0000-0000-0000-000000000000",
            "config_json": config,
            "risk_settings": {} 
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {"x-user-id": user_id}
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        strategy_id = data.get("data", {}).get("id", "unknown")
                        return f"Successfully deployed strategy. ID: {strategy_id}"
                    else:
                        txt = await resp.text()
                        return f"Failed to deploy: {resp.status} - {txt}"
            except Exception as e:
                logger.error(f"AlphaDeployerTool error: {e}")
                return f"Error deploying: {str(e)}"
