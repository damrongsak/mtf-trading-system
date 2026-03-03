import asyncio
import sys
import os

# Inside container, /app is the root
sys.path.append('/app')

from app.risk.risk_limits import RiskLimitsAgent

async def test_icmarkets_limits():
    print("\nMTF Olympus: Testing IC Markets 0.01 Lot Guardrail...")
    
    test_cases = [
        {"symbol": "XAU_USD", "units": 0.5, "desc": "Gold 0.005 Lot", "expected": "PASS"},
        {"symbol": "XAU_USD", "units": 1.0, "desc": "Gold 0.01 Lot", "expected": "PASS"},
        {"symbol": "XAU_USD", "units": 1.1, "desc": "Gold 0.011 Lot", "expected": "FAIL"},
        {"symbol": "EUR_USD", "units": 500, "desc": "Forex 0.005 Lot", "expected": "PASS"},
        {"symbol": "EUR_USD", "units": 1000, "desc": "Forex 0.01 Lot", "expected": "PASS"},
        {"symbol": "EUR_USD", "units": 1001, "desc": "Forex 0.01001 Lot", "expected": "FAIL"},
    ]
    
    passed_all = True
    for tc in test_cases:
        try:
            await RiskLimitsAgent.check_order_size(tc['symbol'], tc['units'])
            result = "PASS"
        except ValueError as e:
            result = "FAIL"
            # print(f"  Reason: {e}")
            
        status = "✅" if result == tc['expected'] else "❌"
        if result != tc['expected']: passed_all = False
        
        print(f"[{status}] {tc['desc']:<25} | Result: {result:<5} | Expected: {tc['expected']}")

    if passed_all:
        print("\n✅ ALL IC MARKETS LIMIT TESTS PASSED. 0.01 Lot Guardrail is ACTIVE.")
    else:
        print("\n❌ SOME TESTS FAILED.")

if __name__ == "__main__":
    asyncio.run(test_icmarkets_limits())
