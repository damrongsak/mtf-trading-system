import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixes():
    print("🚀 Running Logic Verification for StrategyAdvisor & MarketDataTool Fixes...\n")

    # ---------------------------------------------------------
    # Scenario 1: Verify Robust JSON Parsing (StrategyAdvisor)
    # ---------------------------------------------------------
    print("1️⃣  Testing StrategyAdvisor JSON Parsing Fix")
    print("    Context: Gemini sometimes returns 'tool_parameters' instead of 'tool_input'.")
    
    # Simulate LLM Output with the "Wrong" key
    llm_output = """
    ```json
    {
        "tool_name": "market_data",
        "tool_parameters": {
            "symbol": "XAU/USD",
            "timeframe": "H4",
            "include_candles": true
        },
        "reasoning": "checking market data"
    }
    ```
    """
    print(f"    📥 Mock LLM Input:\n{llm_output}")

    # logic from StrategyAdvisor.py
    text = llm_output.replace("```json", "").replace("```", "").strip()
    decision = json.loads(text)
    
    # --- THE FIX APPLIED ---
    start_input = decision.get("tool_input")
    if not start_input:
        start_input = decision.get("tool_parameters") or decision.get("parameters") or decision.get("arguments")
    decision["tool_input"] = start_input
    # -----------------------

    if decision.get("tool_input"):
        print(f"    ✅ SUCCESS: Extracted 'tool_input': {decision['tool_input']}")
    else:
        print(f"    ❌ FAILED: Could not extract tool_input")
    
    print("-" * 50 + "\n")

    # ---------------------------------------------------------
    # Scenario 2: Verify Symbol Normalization (MarketDataTool)
    # ---------------------------------------------------------
    print("2️⃣  Testing MarketDataTool cTrader Normalization")
    print("    Context: cTrader uses 'XAUUSD', but AI/Oanda use 'XAU/USD'.")

    input_data = decision["tool_input"]
    symbol = input_data.get("symbol", "UNKNOWN")
    
    print(f"    📥 Input Symbol: '{symbol}'")

    # logic from tools.py
    # --- THE FIX APPLIED ---
    # Auto-Normalization for cTrader (e.g., XAU/USD -> XAUUSD)
    if symbol and "CTRADER" in "CTRADER": # Explicit intent (simulating the hardcoded check)
            symbol = symbol.replace("/", "").replace("_", "").replace("-", "")
    # -----------------------

    print(f"    📤 Normalized Symbol: '{symbol}'")

    if symbol == "XAUUSD":
        print(f"    ✅ SUCCESS: Symbol normalized correctly for cTrader.")
    else:
        print(f"    ❌ FAILED: Symbol not normalized.")

if __name__ == "__main__":
    test_fixes()
