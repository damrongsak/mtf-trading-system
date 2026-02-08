from pydantic import BaseModel
from typing import Any

class BaseTool(BaseModel):
    name: str
    description: str
    
    async def run(self, input_data: Any, auth_token: str = None) -> Any:
        raise NotImplementedError
