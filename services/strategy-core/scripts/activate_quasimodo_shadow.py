import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.strategy import Strategy
import uuid

def activate_shadow():
    db = SessionLocal()
    try:
        # demo1 Fund: Demo Full System Test Fund
        fund_id = "bdbbd139-3fc4-4ad5-ac9d-b680f77c1bf5"
        # demo1 OANDA Practice Account
        broker_account_id = "f673322d-327a-422d-8888-222222222222" # Placeholder from previous lookup if available, otherwise find it
        
        # Look up any broker account for this fund (Demo/Practice preferred)
        from sqlalchemy import text
        result = db.execute(text("SELECT id FROM broker_accounts WHERE fund_id = :f_id LIMIT 1"), {"f_id": fund_id}).fetchone()
        if not result:
            print("❌ No Practice account found for demo1 fund.")
            return
        
        broker_account_id = str(result[0])
        print(f"✅ Found Broker Account: {broker_account_id}")

        # Check if already exists
        existing = db.query(Strategy).filter(
            Strategy.fund_id == fund_id,
            Strategy.template_id == "quasimodo_v1" # We use v1 as the identifier since registry uses it
        ).first()

        config = {
            "symbol": "XAUUSD",
            "timeframe": "15min",
            "swing_strength": 1,
            "ema_fast": 13,
            "ema_slow": 50,
            "ema_macro": 200,
            "rl_filter_threshold": 0.4
        }

        if existing:
            print(f"Updating existing strategy: {existing.id}")
            existing.is_active = True
            existing.is_shadow = True
            existing.config_json = config
            existing.broker_account_id = broker_account_id
        else:
            print("Creating new shadow strategy instance...")
            new_strat = Strategy(
                id=uuid.uuid4(),
                fund_id=fund_id,
                name="Quasimodo V2 Shadow",
                template_id="quasimodo_v1",
                broker_account_id=broker_account_id,
                config_json=config,
                risk_settings={"risk_pct": 0.01, "max_sl_pips": 40},
                is_active=True,
                is_shadow=True
            )
            db.add(new_strat)
        
        db.commit()
        print("🚀 Quasimodo V2 Shadow Run ACTIVATED.")

    finally:
        db.close()

if __name__ == "__main__":
    activate_shadow()
