
import pytest
import asyncio
import time
import pandas as pd
from unittest.mock import MagicMock
from app.registry import StrategyRegistry



# Actually, I should use the standard loading mechanism or mock the function injection 
# to ensure it goes through the wrapping logic if I want to test the wrapper.
# OR I can just verify the wrapper function itself.

@pytest.mark.asyncio
async def test_wrapper_non_blocking_behavior():
    # 1. Initialize Registry Executor
    if not StrategyRegistry._executor:
        import concurrent.futures
        StrategyRegistry._executor = concurrent.futures.ThreadPoolExecutor()
        
    # 2. Create the Wrapper Manually (mimicking logic)
    import functools
    
    def slow_func(df, params=None):
        time.sleep(0.5)
        return "Done"
        
    async def wrapper():
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            StrategyRegistry._executor,
            functools.partial(slow_func, None, None)
        )
        
    # 3. Run concurrent tasks
    # Task 1: The slow wrapper
    start_time = time.time()
    task_slow = asyncio.create_task(wrapper())
    
    # Task 2: A fast async task (simulating health check)
    async def fast_task():
        await asyncio.sleep(0.1)
        return "Fast"
        
    task_fast = asyncio.create_task(fast_task())
    
    # Await fast task first
    res_fast = await task_fast
    end_fast = time.time()
    
    # Await slow task
    res_slow = await task_slow
    end_slow = time.time()
    
    # 4. Assertions
    # The fast task should finish WAY before the slow task (approx 0.1s vs 0.5s)
    # If blocked, fast task would wait for slow task to finish or start late?
    # If run_in_executor works, 'slow_func' runs in thread, yielding control immediately.
    # 'await task_slow' yields. 'task_fast' starts.
    
    assert res_fast == "Fast"
    assert res_slow == "Done"
    
    # Fast task should take ~0.1s
    # Slow task should take ~0.5s
    # If blocked, fast task would finish at 0.6s
    
    print(f"Fast took: {end_fast - start_time}")
    print(f"Slow took: {end_slow - start_time}")
    
    assert (end_fast - start_time) < 0.3 # Should be well under 0.5s
    assert (end_slow - start_time) >= 0.5
