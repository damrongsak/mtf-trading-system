import asyncio
import json
import logging
import os
import traceback
from contextlib import AsyncExitStack

from redis.asyncio import Redis
from app.core.globals import services
from app.core.bootstrap import bootstrap_tools
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService
from app.services.episodic_memory import EpisodicMemoryService
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.agents.post_mortem import PostMortemAgent
from app.agents.trade_manager import TradeManagementAgent
from app.agents.risk_rebalancer import RiskRebalancerAgent
from app.database import SessionLocal
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings

logger = logging.getLogger("ai-analyst-worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_KEY = "ai:think:cmd"
GROUP_NAME = "ai_analyst_workers"
CONSUMER_NAME = f"worker-{os.getpid()}"

async def bootstrap_worker(stack: AsyncExitStack):
    logger.info("Bootstrapping AI Analyst Worker...")
    
    # 1. Redis Bus
    redis_bus = Redis.from_url(REDIS_URL, decode_responses=True)
    services["redis"] = redis_bus
    
    # 2. Tools & Gemini
    bootstrap_tools()
    services["gemini"] = GeminiClient()
    services["rag"] = RAGService(services["gemini"])
    services["memory"] = MemoryService(services["rag"])
    
    db = SessionLocal()
    services["episodic_memory_service"] = EpisodicMemoryService(db)
    
    # 3. Checkpointer
    services["checkpointer"] = MemorySaver()
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        services["checkpointer"] = await stack.enter_async_context(
            AsyncRedisSaver.from_conn_string(settings.redis.url)
        )
    except Exception as e:
        logger.warning(f"Redis Checkpointer Failed: {e}. Fallback to MemorySaver")
        
    # 4. Agents (Dependencies for StrategyAdvisor)
    services["post_mortem"] = PostMortemAgent(services["gemini"], services["rag"])
    services["trade_manager"] = TradeManagementAgent(services["gemini"])
    services["risk_rebalancer"] = RiskRebalancerAgent(services["gemini"])
    
    services["strategy_advisor"] = StrategyAdvisorAgent(
        services["rag"], 
        services["gemini"], 
        checkpointer=services["checkpointer"],
        memory_service=services["memory"],
        post_mortem_agent=services["post_mortem"],
        trade_manager_agent=services["trade_manager"],
        risk_rebalancer_agent=services["risk_rebalancer"],
        episodic_memory_service=services["episodic_memory_service"]
    )
    logger.info("Worker bootstrap complete.")
    return redis_bus

async def process_job(redis_client: Redis, job_id: str, payload: dict, headers: dict):
    logger.info(f"Processing job {job_id}")
    try:
        # Extract params
        message = payload.get("message", "")
        intent = payload.get("intent")
        image_b64 = payload.get("image_b64")
        thread_id = payload.get("thread_id")
        
        # User ID extraction
        auth_token = None
        target_user_id = "unified_user"
        auth_header = headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
            try:
                import jwt
                decoded = jwt.decode(auth_token, options={"verify_signature": False})
                target_user_id = decoded.get("sub") or decoded.get("user_id") or target_user_id
            except:
                pass
                
        # Run
        result = await services["strategy_advisor"].run(
            input_text=message,
            user_id=target_user_id,
            auth_token=auth_token,
            image_b64=image_b64,
            thread_id=thread_id,
            intent_hint=intent,
            trade_id=payload.get("trade_id"),
            is_journal_job=payload.get("is_journal_job", False)
        )
        
        result_payload = {
            "status": "completed", 
            "data": {
                "response": result.get("response", "No response generated"),
                "intent_resolved": result.get("intent_resolved", "general"),
                "severity": result.get("severity", "ROUTINE"),
                "metadata": result.get("metadata", {}),
                "timestamp": result.get("timestamp")
            }
        }
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}\n{traceback.format_exc()}")
        result_payload = {"status": "error", "error": str(e)}
        
    await redis_client.set(f"ai:think:result:{job_id}", json.dumps(result_payload), ex=86400)
    logger.info(f"Finished job {job_id}, status={result_payload['status']}")

async def main():
    async with AsyncExitStack() as stack:
        redis_client = await bootstrap_worker(stack)
        
        # Ensure stream exists
        try:
            await redis_client.xadd(STREAM_KEY, {"init": "1"})
            logger.info(f"Stream {STREAM_KEY} ensured.")
        except:
            pass
            
        try:
            await redis_client.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
            logger.info(f"Consumer group {GROUP_NAME} created.")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create group: {e}")
                
        logger.info(f"Started AI Analyst Worker listening on {STREAM_KEY}")
        
        while True:
            try:
                messages = await redis_client.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_KEY: '>'}, count=1, block=5000
                )
                if messages:
                    for stream, msg_list in messages:
                        for msg_id, msg_data in msg_list:
                            job_id = msg_data.get("job_id")
                            payload = json.loads(msg_data.get("payload", "{}"))
                            headers = json.loads(msg_data.get("headers", "{}"))
                            
                            await process_job(redis_client, job_id, payload, headers)
                            await redis_client.xack(STREAM_KEY, GROUP_NAME, msg_id)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
