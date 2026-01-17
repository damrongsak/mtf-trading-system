import logging
import asyncio
import redis.asyncio as redis
from typing import Optional, Dict, List, AsyncGenerator, Any

logger = logging.getLogger(__name__)

class RedisStreamClient:
    """
    A robust, async wrapper for consuming Redis Streams.
    Handles connection, consumer groups, and message iteration.
    """
    def __init__(
        self, 
        redis_url: str, 
        stream_key: str, 
        group_name: str, 
        consumer_name: str
    ):
        self.redis_url = redis_url
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.redis: Optional[redis.Redis] = None
        self.running = False

    async def connect(self):
        """Initializes the Redis connection and ensures the Consumer Group exists."""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        try:
            # Create group. MKSTREAM=True creates the stream if it doesn't exist.
            # id="$" means only new messages (if first time).
            # If we want replay, we'd manage that elsewhere, but usually services start fresh or resume.
            await self.redis.xgroup_create(
                self.stream_key, 
                self.group_name, 
                id="$", 
                mkstream=True
            )
            logger.info(f"Created consumer group {self.group_name} for {self.stream_key}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {self.group_name} already exists.")
            else:
                logger.error(f"Failed to create consumer group: {e}")
                raise e
        
        self.running = True

    async def close(self):
        """Closes the Redis connection."""
        self.running = False
        if self.redis:
            await self.redis.close()

    async def consume(self, batch_size: int = 10, block_ms: int = 2000) -> AsyncGenerator[tuple[str, Dict[str, Any]], None]:
        """
        Yields messages from the stream indefinitely.
        Returns: (message_id, fields_dict)
        """
        if not self.redis:
             raise RuntimeError("Redis client not connected. Call connect() first.")

        logger.info(f"Started consuming {self.stream_key} as {self.consumer_name}")
        
        while self.running:
            try:
                # READGROUP
                # ">" means "messages never delivered to other consumers in this group"
                streams = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=batch_size,
                    block=block_ms
                )

                if not streams:
                    continue

                for stream_name, messages in streams:
                    for message_id, fields in messages:
                        yield message_id, fields

            except asyncio.CancelledError:
                logger.info("Consumption cancelled.")
                break
            except Exception as e:
                logger.error(f"Error consuming stream: {e}")
                await asyncio.sleep(1) # Backoff

    async def ack(self, message_id: str):
        """Acknowledges a message as processed."""
        if self.redis:
            await self.redis.xack(self.stream_key, self.group_name, message_id)
