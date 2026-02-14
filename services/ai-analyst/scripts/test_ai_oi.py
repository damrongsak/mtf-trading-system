import asyncio
import logging
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.core.globals import services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-ai-oi")

async def test_ai_oi():
    logger.info("Testing AI Analyst with question: 'give me OI Support zone'")
    
    # Initialize necessary services
    gemini = GeminiClient()
    rag = RAGService(gemini)
    services["gemini"] = gemini
    services["rag"] = rag
    
    agent = StrategyAdvisorAgent(rag, gemini)
    
    # Run the agent
    result = await agent.run(
        input_text="give me OI Support zone",
        user_id="test_user"
    )
    
    print("\n--- AI Analyst Response ---\n")
    print(result.get("response"))
    print("\n--- End of Response ---\n")

if __name__ == "__main__":
    asyncio.run(test_ai_oi())
