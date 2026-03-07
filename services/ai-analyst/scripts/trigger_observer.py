import asyncio
import logging
from app.core.globals import services
from app.core.bootstrap import bootstrap_tools
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.strategy_advisor import StrategyAdvisorAgent
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Manual Observer Trigger...")
    
    # 1. Bootstrap
    bootstrap_tools()
    
    # 2. Setup minimum services for agent
    gemini = GeminiClient()
    rag = RAGService(gemini)
    checkpointer = MemorySaver()
    
    agent = StrategyAdvisorAgent(
        rag_service=rag,
        gemini_client=gemini,
        checkpointer=checkpointer
    )
    
    # 3. Run Observer Report
    input_text = "Generate a comprehensive market situation report for XAU/USD, EUR/USD, and GBP/USD based on current technical data and SMC patterns."
    
    logger.info(f"Running Agent with input: {input_text}")
    
    try:
        result = await agent.run(
            input_text=input_text,
            user_id="manual_test_user",
            auth_token=None # Tools might fail if they REQUIRE auth, but let's see.
        )
        
        logger.info("\n" + "="*50)
        logger.info("ROBOT RESPONSE:")
        logger.info("="*50)
        logger.info(result.get("response", "No response content"))
        logger.info("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
