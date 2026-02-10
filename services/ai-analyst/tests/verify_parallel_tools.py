import asyncio
import time
import unittest
from unittest.mock import MagicMock, AsyncMock
from app.agents.strategy_advisor import StrategyAdvisorAgent

# Mock Tool
class MockTool:
    def __init__(self, name, delay=1.0):
        self.name = name
        self.delay = delay
        
    async def run(self, input_data, auth_token=None):
        print(f"[{self.name}] Starting... (sleeping {self.delay}s)")
        await asyncio.sleep(self.delay)
        print(f"[{self.name}] Finished!")
        return f"Result from {self.name}"

class TestParallelExecution(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_tools(self):
        # Mock Dependencies
        mock_rag = MagicMock()
        mock_gemini = MagicMock()
        
        # Instantiate Agent (partial)
        agent = StrategyAdvisorAgent(mock_rag, mock_gemini)
        
        # Mock Tool Registry
        agent.tool_registry = MagicMock()
        
        # Setup Tools
        tool1 = MockTool("tool1", delay=1.0)
        tool2 = MockTool("tool2", delay=1.0)
        
        def get_tool_side_effect(name):
            if name == "tool1": return tool1
            if name == "tool2": return tool2
            return None
            
        agent.tool_registry.get_tool.side_effect = get_tool_side_effect
        
        # Define State
        state = {
            "tool_calls": [
                {"tool_name": "tool1", "tool_input": "{}"},
                {"tool_name": "tool2", "tool_input": "{}"}
            ],
            "auth_token": "fake_token",
            "scratchpad": []
        }
        
        print("\n--- Starting Parallel Execution Test ---")
        start_time = time.time()
        
        # Run node
        result = await agent.node_execute_tools(state)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"--- Test Finished in {duration:.2f} seconds ---")
        print(f"Outputs: {result['scratchpad']}")
        
        # Assertions
        # If parallel, duration should be close to 1.0s (e.g. < 1.1s)
        # If sequential, duration would be > 2.0s
        self.assertLess(duration, 1.2, "Execution took too long! Likely sequential.")
        self.assertEqual(len(result['scratchpad']), 2)
        print("✅ Parallel execution verified successfully.")

if __name__ == "__main__":
    unittest.main()
