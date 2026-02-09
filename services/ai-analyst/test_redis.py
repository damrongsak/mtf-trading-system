import asyncio
from contextlib import AsyncExitStack
from langgraph.checkpoint.redis import AsyncShallowRedisSaver

async def test():
    async with AsyncExitStack() as stack:
        try:
            url = 'redis://redis:6379/0'
            cm = AsyncShallowRedisSaver.from_conn_string(url)
            print(f'Shallow CM type: {type(cm)}')
            
            print("Attempting to enter context...")
            saver = await stack.enter_async_context(cm)
            
            print(f'Entered Saver type: {type(saver)}')
            print(f'Saver has get_next_version: {hasattr(saver, "get_next_version")}')
            
            if hasattr(saver, "get_next_version"):
                print("SUCCESS: Shallow Saver is correctly initialized and available.")
            else:
                print("FAILURE: Shallow Saver lacks get_next_version method.")
                
        except Exception as e:
            print(f"Caught Exception: {e} ({type(e)})")

if __name__ == "__main__":
    asyncio.run(test())
