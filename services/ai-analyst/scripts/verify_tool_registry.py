
from app.core.tools import ToolRegistry
from app.services.rag import RAGService
from app.services.gemini import GeminiClient

# Mock RAG
rag = None 
registry = ToolRegistry(rag)
tools = registry.tools.keys()
print(f"Registered tools: {list(tools)}")
if "open_claw_research" in tools:
    print("SUCCESS: open_claw_research is in ToolRegistry")
else:
    print("FAILURE: open_claw_research is NOT in ToolRegistry")
