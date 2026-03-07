import asyncio
import logging
import json
import os
import socket
from typing import Dict, Any
import redis.asyncio as redis
from app.database import SessionLocal
from app.models.sentiment_score import SentimentScore

logger = logging.getLogger(__name__)

class SentimentWorker:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.running = False
        self.batch_size = 10
        self.stream_key = "market.sentiment.stream"
        self.group_name = "sentiment_persistence_group"
        self.consumer_name = os.getenv("HOSTNAME", socket.gethostname())

    async def start(self):
        self.running = True
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"SentimentWorker connected to Redis at {self.redis_url}")
        
        # Create Consumer Group
        await self._ensure_group_exists()
        
        asyncio.create_task(self._consume_loop())

    async def _ensure_group_exists(self):
        try:
            # Create group, start from beginning if it doesn't exist (replaying history)
            await self.redis.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group {self.group_name}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group {self.group_name} already exists.")
            else:
                logger.error(f"Group create error: {e}")

    async def stop(self):
        self.running = False
        if self.redis:
            await self.redis.close()

    async def _consume_loop(self):
        logger.info("SentimentWorker loop started.")
        while self.running:
            try:
                # Read new messages
                streams = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=1000
                )

                if not streams:
                    continue

                for stream, messages in streams:
                    for message_id, fields in messages:
                        await self.process_sentiment(message_id, fields)
                        # Ack processing
                        await self.redis.xack(self.stream_key, self.group_name, message_id)

            except Exception as e:
                if "NOGROUP" in str(e):
                    logger.warning(f"Consumer group missing (NOGROUP). Attempting to recreate...")
                    await self._ensure_group_exists()
                else:
                    logger.error(f"SentimentWorker loop/consumption error: {e}")
                
                await asyncio.sleep(5)

    async def process_sentiment(self, message_id: str, fields: Dict[str, Any]):
        try:
            # Fields from Redis stream are usually strings
            symbol = fields.get("symbol")
            score = float(fields.get("score", 0.0))
            reason = fields.get("reason")
            source_breakdown = fields.get("source_breakdown")
            
            if source_breakdown and isinstance(source_breakdown, str):
                try:
                    source_breakdown = json.loads(source_breakdown)
                except:
                    source_breakdown = {}

            db = SessionLocal()
            try:
                sentiment = SentimentScore(
                    symbol=symbol,
                    score=score,
                    reason=reason,
                    source_breakdown=source_breakdown
                )
                db.add(sentiment)
                db.commit()
                logger.info(f"SentimentWorker: Persisted sentiment for {symbol}: {score}")
            except Exception as db_err:
                logger.error(f"Failed to persist sentiment to DB: {db_err}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing sentiment message {message_id}: {e}")

# Global instance for easy access
sentiment_worker = SentimentWorker()
