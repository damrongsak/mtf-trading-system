import asyncio
import logging
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini import GeminiClient
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.rag import RAGService
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_routing():
    logger.info("🚀 Starting AI Scaling Verification (v2.5)")
    
    gemini = GeminiClient()
    rag = MagicMock(spec=RAGService)
    
    # Mock specialist agents
    mock_post_mortem = MagicMock()
    mock_trade_manager = MagicMock()
    
    agent = StrategyAdvisorAgent(
        rag, 
        gemini, 
        post_mortem_agent=mock_post_mortem,
        trade_manager_agent=mock_trade_manager
    )
    
    test_cases = [
        {
            "input": "Can you analyze my last 5 trades and tell me what I learned?",
            "expected_intent": "JOURNAL_ANALYSIS"
        },
        {
            "input": "Check my open positions and move SL to break-even if they are in profit.",
            "expected_intent": "PORTFOLIO_MANAGEMENT"
        },
        {
            "input": "How is the gold market looking today?",
            "expected_intent": "MARKET_REPORT"
        }
    ]
    
    for case in test_cases:
        logger.info(f"\n📝 Testing Input: '{case['input']}'")
        # We only need to run the query optimizer node to verify intent classification
        state = {
            "input_text": case["input"],
            "messages": [],
            "user_id": "test_user",
            "auth_token": "mock_token",
            "scratchpad": [],
            "severity": "ROUTINE"
        }
        
        result = await agent.node_query_optimizer(state)
        resolved_intent = result.get("intent")
        
        if resolved_intent == case["expected_intent"]:
            logger.info(f"✅ SUCCESS: Resolved intent '{resolved_intent}' matches expected.")
        else:
            logger.error(f"❌ FAILURE: Resolved intent '{resolved_intent}', expected '{case['expected_intent']}'")

    logger.info("\n✨ Verification Complete")

if __name__ == "__main__":
    asyncio.run(verify_routing())
