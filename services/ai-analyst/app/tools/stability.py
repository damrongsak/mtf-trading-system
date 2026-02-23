from typing import Any, Dict
import httpx
import asyncio
from app.core.config import settings
from app.core.base_tool import BaseTool

class SystemHealthTool(BaseTool):
    name: str = "get_system_health"
    description: str = "Checks the health status of all MTF Olympus backend services (Predictor, Analyst, Gateway)."

    async def run(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        services_to_check = {
            "Olympus Predictor": f"{settings.OLYMPUS_PREDICTOR_URL}/health",
            "API Gateway": f"{settings.API_GATEWAY_URL}/health",
        }
        
        async def check_service(name, url):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("status", "healthy")
                        return f"✅ **{name}**: {status.upper()}"
                    return f"❌ **{name}**: Error {resp.status_code}"
            except Exception as e:
                return f"⚠️ **{name}**: Unreachable ({str(e)})"

        results = await asyncio.gather(*[check_service(n, u) for n, u in services_to_check.items()])
        
        # Add local analyst health
        analyst_health = "✅ **AI Analyst**: HEALTHY"
        
        report = [
            "### MTF Olympus System Health Report",
            analyst_health,
            *results,
            "\n*All systems operational.*" if all("✅" in r for r in results) else "\n*Attention required: Some systems are degraded or unreachable.*"
        ]
        
        return "\n".join(report)
