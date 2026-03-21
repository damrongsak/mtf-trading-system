import asyncio
import uuid
import logging
from app.engine.core import StrategyEngine, StrategyState
from app.schemas import ExecutionMode
from app.database import SessionLocal
from app.models.signal_log import SignalLog
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase9Verify")

async def verify_phase9():
    """Manual verification of Knowledge Context injection on the 8GB host."""
    logger.info("🧪 Starting Phase 9 End-to-End Verification...")
    
    engine = StrategyEngine()
    
    # Mock Strategy State for XAUUSD
    strategy_id = "test-phase9-xauusd"
    config = {
        "id": strategy_id,
        "template_id": "bb_stoch_ob_v1",
        "symbol": "XAUUSD",
        "broker_account_id": str(uuid.uuid4()),
        "execution_mode": ExecutionMode.MANUAL,
        "use_sentiment_filter": True
    }
    state = StrategyState(config)
    
    # Mock Signal
    test_signal = {
        "direction": "BULLISH",
        "confidence": 0.85,
        "price": 2574.9,
        "stop_loss": 2560.0,
        "reason": "Knowledge Verification Signal",
        "meta_data": {"test": True}
    }
    
    logger.info("📡 Executing Signal with Knowledge Context...")
    # This should call get_knowledge_context internal to StrategyEngine
    # Note: ai-analyst must be running and reached via http://ai-analyst:8000
    try:
        await engine._execute_signal(strategy_id, state, test_signal)
        logger.info("✅ Signal execution call finished.")
    except Exception as e:
        logger.error(f"❌ Signal execution failed: {e}")
        return

    # Verify DB Persistence
    logger.info("🔍 Verifying DB Persistence for XAUUSD Context...")
    db = SessionLocal()
    try:
        query = select(SignalLog).where(SignalLog.symbol == "XAUUSD").order_by(SignalLog.timestamp.desc()).limit(1)
        result = db.execute(query).scalar_one_or_none()
        
        if result:
            logger.info("📄 Last Signal Log Found:")
            logger.info(f"   ID: {result.id}")
            logger.info(f"   Symbol: {result.symbol}")
            logger.info(f"   Knowledge Score: {result.knowledge_score}")
            logger.info(f"   Knowledge Context Found: {result.knowledge_context is not None}")
            
            if result.knowledge_context:
                logger.info("   Summary Preview: " + result.knowledge_context.get("summary", "No Summary"))
                logger.info("✅ SUCCESS: Phase 9 GraphRAG baseline confirmed.")
            else:
                logger.error("❌ FAILURE: knowledge_context is NULL in DB.")
        else:
            logger.error("❌ FAILURE: No SignalLog found for XAUUSD.")
            
    except Exception as e:
        logger.error(f"❌ DB Verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_phase9())
