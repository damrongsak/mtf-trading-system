
import math

def calculate_units_old(target_risk, dist):
    # แบบเดิมที่ใช้ int()
    units = target_risk / dist
    if abs(units) < 1.0:
        return "FAILED: Below 1 unit"
    return int(units)

def calculate_units_new(target_risk, dist):
    # แบบใหม่ที่ใช้ round(..., 4)
    units = target_risk / dist
    if abs(units) < 0.0001:
        return "FAILED: Below 0.0001 unit"
    return round(units, 4)

# ทดสอบกรณีเสี่ยงต่างๆ
test_cases = [
    {"name": "Small Account ($10 risk, $50 SL dist)", "risk": 10, "dist": 50}, # ควรได้ 0.2
    {"name": "Micro Risk ($1 risk, $100 SL dist)", "risk": 1, "dist": 100},   # ควรได้ 0.01
    {"name": "Standard Gold ($100 risk, $2 SL dist)", "risk": 100, "dist": 2}, # ควรได้ 50.0
]

print(f"{'Test Case':<40} | {'Old (int)':<15} | {'New (round)':<15} | {'Status'}")
print("-" * 85)

for tc in test_cases:
    old = calculate_units_old(tc['risk'], tc['dist'])
    new = calculate_units_new(tc['risk'], tc['dist'])
    status = "✅ FIXED" if old != new and not str(new).startswith("FAILED") else "⚠️ SAME"
    if str(old).startswith("FAILED") and not str(new).startswith("FAILED"):
        status = "✅ FIXED (Now supports micro)"
    print(f"{tc['name']:<40} | {str(old):<15} | {str(new):<15} | {status}")
