import asyncio
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

async def test():
    saver_cm = AsyncRedisSaver.from_conn_string('redis://redis:6379/0')
    print(f'CM type: {type(saver_cm)}')
    async with saver_cm as saver:
        print(f'Saver type in CM: {type(saver)}')
        print(f'Saver has get_next_version: {hasattr(saver, "get_next_version")}')

if __name__ == "__main__":
    asyncio.run(test())
