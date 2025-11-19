"""
Seed script for default risk rules.

This script populates the risk_rules table with the MVP risk guardrails
as defined in the PRD:
- F2.2: $10 maximum risk per trade
- F2.3: 0.01 minimum lot size
- F2.4: 100 pips maximum ATR-based stop loss
- Minimum 1:2 risk-to-reward ratio

Usage:
    python scripts/seed_risk_rules.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.risk_rule import RiskRule, RuleType
import uuid


def seed_risk_rules():
    """Populate risk_rules table with MVP defaults."""

    db = SessionLocal()

    try:
        # Check if rules already exist
        existing_count = db.query(RiskRule).count()
        if existing_count > 0:
            print(f"⚠️  Risk rules already seeded ({existing_count} rules exist). Skipping.")
            return

        # Define MVP risk rules from PRD
        default_rules = [
            {
                "rule_name": "MAX_RISK_PER_TRADE",
                "rule_type": RuleType.RISK_CAP,
                "threshold_value": 10.00,
                "threshold_unit": "USD",
                "is_active": True,
                "description": "F2.2: Absolute risk cap of $10 per trade. This is the most critical guardrail for capital preservation (G1)."
            },
            {
                "rule_name": "MIN_LOT_SIZE",
                "rule_type": RuleType.LOT_SIZE,
                "threshold_value": 0.01,
                "threshold_unit": "LOT",
                "is_active": True,
                "description": "F2.3: Minimum tradable lot size. Trades with calculated lot size below this threshold will be rejected."
            },
            {
                "rule_name": "MAX_ATR_PIPS_SL",
                "rule_type": RuleType.VOLATILITY,
                "threshold_value": 100.00,
                "threshold_unit": "PIPS",
                "is_active": True,
                "description": "F2.4: Volatility guardrail. Trades with ATR-based stop loss exceeding 100 pips will be rejected to avoid high-volatility whipsaws."
            },
            {
                "rule_name": "MIN_RR_RATIO",
                "rule_type": RuleType.RR_RATIO,
                "threshold_value": 2.00,
                "threshold_unit": "RATIO",
                "is_active": True,
                "description": "Minimum risk-to-reward ratio of 1:2. Ensures each trade has asymmetric risk profile favoring the trader."
            }
        ]

        # Insert rules
        for rule_data in default_rules:
            rule = RiskRule(
                rule_id=uuid.uuid4(),
                **rule_data
            )
            db.add(rule)
            print(f"✓ Created rule: {rule.rule_name} = {rule.threshold_value} {rule.threshold_unit}")

        db.commit()
        print(f"\n✅ Successfully seeded {len(default_rules)} risk rules!")

        # Verify
        total = db.query(RiskRule).count()
        print(f"📊 Total risk rules in database: {total}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding risk rules: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding risk rules...")
    seed_risk_rules()
