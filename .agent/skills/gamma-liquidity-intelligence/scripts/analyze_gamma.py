import json
import sys

def analyze_gex_regime(data, spot_price):
    """
    Analyzes raw gamma data and provides an actionable summary.
    """
    regime_data = data.get('regime', {})
    regime_type = regime_data.get('regime', 'UNKNOWN')
    flip_level = regime_data.get('gamma_flip_level')
    max_pain = data.get('max_pain', 0.0)
    
    # 1. Determine Bias
    if spot_price > 0 and flip_level:
        bias = "BULLISH" if spot_price > flip_level else "BEARISH"
    else:
        bias = "NEUTRAL"

    # 2. Risk Evaluation
    risk_multiplier = 1.0 if regime_type == 'POSITIVE_GAMMA' else 0.5
    
    # 3. Pull Key Walls
    levels = data.get('levels', [])
    major_resistance = [l for l in levels if l['type'] == 'CALL_WALL' and l['zone_type'] == 'MAJOR']
    major_support = [l for l in levels if l['type'] == 'PUT_WALL' and l['zone_type'] == 'MAJOR']
    
    # 4. Proximity to Max Pain
    pain_dist = abs(spot_price - max_pain) / spot_price if spot_price > 0 else 0
    gravity_alert = pain_dist > 0.03 # 3% distance
    
    summary = {
        "regime": regime_type,
        "institutional_bias": bias,
        "risk_multiplier": risk_multiplier,
        "gamma_flip": flip_level,
        "max_pain": max_pain,
        "major_resistance": major_resistance[0]['price'] if major_resistance else None,
        "major_support": major_support[0]['price'] if major_support else None,
        "gravity_warning": "HIGH" if gravity_alert else "NORMAL"
    }
    
    return summary

if __name__ == "__main__":
    # Expects JSON data and spot_price as arguments
    try:
        raw_data = json.loads(sys.argv[1])
        spot = float(sys.argv[2])
        result = analyze_gex_regime(raw_data, spot)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
