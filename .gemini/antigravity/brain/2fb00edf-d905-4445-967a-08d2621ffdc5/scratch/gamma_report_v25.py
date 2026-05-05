import os
import pandas as pd
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer
import redis

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SYMBOL = "XAUUSD"

def get_current_spot():
    try:
        r = redis.from_url(REDIS_URL)
        data = r.hgetall("market_data:spot:OANDA:XAUUSD")
        if data:
            return float(data.get(b'bid', 2350))
    except Exception:
        pass
    return 2350.0 # Fallback

def run_analysis():
    engine = create_engine(DATABASE_URL)
    analyzer = LiquidityProfileAnalyzer()
    spot_price = get_current_spot()
    
    # 1. Fetch Latest Snapshot
    query = text("""
        SELECT * FROM open_interest 
        WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM open_interest WHERE contract_symbol LIKE 'OG%')
        AND contract_symbol LIKE 'OG%'
        AND dte <= 60
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        print("Error: No institutional data found.")
        return

    # 2. Convert to list of dicts for analyzer
    records = df.to_dict('records')
    
    # 3. Analyze
    result = analyzer.analyze_snapshot(records, current_spot_price=spot_price)
    regime = result['regime']
    
    # 4. Generate Report
    report = f"""
# 🔱 MTF Olympus: Gamma & GEX Analysis Report (V2.5)
**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
**Asset:** XAUUSD (Gold)
**Market Reality (Spot):** {spot_price:,.2f}

## 📊 Market Regime Summary
- **Current Regime:** {'🟢 Positive Gamma' if regime.regime == 'POSITIVE_GAMMA' else '🔴 Negative Gamma'}
- **Net GEX Total:** ${regime.net_gex / 1_000_000_000:,.2f}B
- **Gamma Flip Level:** {regime.gamma_flip_level:,.2f}
- **Market State:** {'Mean Reversion / Low Volatility' if regime.regime == 'POSITIVE_GAMMA' else 'Trend Following / High Volatility'}

## 🛡️ Key Liquidity Walls
- **Call Wall (Resistance):** {result['levels'].get('call_wall', 'N/A')}
- **Put Wall (Support):** {result['levels'].get('put_wall', 'N/A')}
- **Institutional Scale:** $100 per 1.0 Gamma unit

## ⚠️ Fragility & Risk (LFI)
- **Fragility Index:** {regime.fragility_index:.1f}%
- **Institutional Bias:** {result.get('institutional_bias', 'STABLE')}
- **Vanna/Charm Sensitivity:** {'High (Delta hedging active)' if regime.fragility_index > 60 else 'Low (Stable liquidity)'}

---
**Institutional Mandate:** All calculations anchored to CME OG Options (DTE <= 60).
"""
    print(report)

if __name__ == "__main__":
    run_analysis()
