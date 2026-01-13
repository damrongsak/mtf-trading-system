"""
Seed script for test/example data.

This script populates the database with sample users, funds, and journal entries
for development and testing purposes.

Usage:
    python scripts/seed_test_data.py
    
    # Or with custom options:
    python scripts/seed_test_data.py --users 5 --entries 20
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.user import User
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.security import get_password_hash
import uuid


def seed_users(db, count=3):
    """Create sample users."""
    print(f"\n📝 Creating {count} test users...")
    
    users_data = [
        {
            "username": "trader1",
            "email": "trader1@example.com",
            "password": "password123",
            "is_superuser": False
        },
        {
            "username": "trader2",
            "email": "trader2@example.com",
            "password": "password123",
            "is_superuser": False
        },
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",
            "is_superuser": True
        },
    ]
    
    created_users = []
    for user_data in users_data[:count]:
        # Check if user already exists
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if existing:
            print(f"  ⚠️  User '{user_data['username']}' already exists, skipping")
            created_users.append(existing)
            continue
        
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
            is_active=True,
            is_superuser=user_data["is_superuser"]
        )
        db.add(user)
        created_users.append(user)
        print(f"  ✓ Created user: {user.username} (password: {user_data['password']})")
    
    db.commit()
    return created_users


def seed_funds(db, users, count=2):
    """Create sample funds."""
    print(f"\n💰 Creating {count} test funds...")
    
    funds_data = [
        {
            "name": "Alpha Trading Fund",
            "description": "Main trading fund for XAU/USD strategies"
        },
        {
            "name": "Beta Testing Fund",
            "description": "Fund for testing new strategies"
        },
    ]
    
    created_funds = []
    for fund_data in funds_data[:count]:
        # Check if fund already exists
        existing = db.query(Fund).filter(Fund.name == fund_data["name"]).first()
        if existing:
            print(f"  ⚠️  Fund '{fund_data['name']}' already exists, skipping")
            created_funds.append(existing)
            continue
        
        fund = Fund(
            name=fund_data["name"],
            description=fund_data["description"]
        )
        db.add(fund)
        created_funds.append(fund)
        print(f"  ✓ Created fund: {fund.name}")
    
    db.commit()
    
    # Assign users to funds
    print(f"\n🔗 Assigning users to funds...")
    for i, user in enumerate(users):
        for j, fund in enumerate(created_funds):
            # Check if relationship already exists
            existing = db.query(UserFund).filter(
                UserFund.user_id == user.id,
                UserFund.fund_id == fund.id
            ).first()
            
            if existing:
                continue
            
            # Assign role based on user type
            role = UserRole.OWNER if user.is_superuser else UserRole.TRADER
            
            user_fund = UserFund(
                user_id=user.id,
                fund_id=fund.id,
                role=role
            )
            db.add(user_fund)
            print(f"  ✓ Assigned {user.username} to {fund.name} as {role.value}")
    
    db.commit()
    return created_funds


def seed_journal_entries(db, users, count=10):
    """Create sample journal entries."""
    print(f"\n📔 Creating {count} test journal entries...")
    
    symbols = ["XAU/USD", "EUR/USD", "GBP/USD"]
    directions = ["LONG", "SHORT"]
    sessions = ["LONDON", "NEW_YORK", "ASIAN"]
    game_levels = ["A_GAME", "B_GAME", "C_GAME"]
    
    created_entries = []
    for i in range(count):
        user = random.choice(users)
        symbol = random.choice(symbols)
        direction = random.choice(directions)
        
        # Generate realistic trade data
        entry_price = random.uniform(1800, 2000) if symbol == "XAU/USD" else random.uniform(1.05, 1.15)
        is_winner = random.random() > 0.4  # 60% win rate
        
        if is_winner:
            exit_price = entry_price + random.uniform(5, 20) if direction == "LONG" else entry_price - random.uniform(5, 20)
            pnl_amount = random.uniform(10, 50)
            pnl_r = random.uniform(1.5, 4.0)
        else:
            exit_price = entry_price - random.uniform(3, 10) if direction == "LONG" else entry_price + random.uniform(3, 10)
            pnl_amount = -random.uniform(5, 10)
            pnl_r = -1.0
        
        # Create journal entry FIRST
        entry = JournalEntry(
            user_id=user.id,
            symbol=symbol,
            direction=direction,
            session=random.choice(sessions),
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_amount=pnl_amount,
            pnl_r=pnl_r,
            risk_amount=10.0,
            stop_loss_price=entry_price - 10 if direction == "LONG" else entry_price + 10,
            take_profit_price=entry_price + 20 if direction == "LONG" else entry_price - 20,
            context_score=random.randint(5, 10),
            game_level=random.choice(game_levels),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        db.add(entry)
        db.flush()  # Get the entry ID
        
        # Now create related objects with journal_entry_id
        mental_state = MentalState(
            journal_entry_id=entry.id,
            greed_level=random.randint(1, 10),
            fear_level=random.randint(1, 10),
            tilt_level=random.randint(1, 10),
            confidence_level=random.randint(1, 10),
            discipline_level=random.randint(1, 10)
        )
        db.add(mental_state)
        
        # Create timeline events
        timeline_events = [
            TimelineEvent(
                journal_entry_id=entry.id,
                type="ENTRY",
                description="Entered trade based on 4H order block",
                order_index=1,
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
            ),
            TimelineEvent(
                journal_entry_id=entry.id,
                type="MANAGEMENT",
                description="Moved stop loss to breakeven",
                order_index=2,
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 24))
            ),
            TimelineEvent(
                journal_entry_id=entry.id,
                type="EXIT",
                description="Closed at TP level" if is_winner else "Stopped out",
                order_index=3,
                timestamp=datetime.utcnow()
            )
        ]
        for event in timeline_events:
            db.add(event)
        
        # Create root cause analysis
        root_cause = RootCauseAnalysis(
            journal_entry_id=entry.id,
            problem="Entered too early" if not is_winner else None,
            why_exist="Impatience, wanted to catch the move" if not is_winner else None,
            flaw="Not waiting for 15m confirmation" if not is_winner else None,
            correction="Wait for body-to-wick ratio confirmation" if not is_winner else None,
            logic="Follow the MTF checklist strictly" if not is_winner else "Good execution, followed plan"
        )
        db.add(root_cause)
        
        created_entries.append(entry)
        print(f"  ✓ Created journal entry: {symbol} {direction} (PnL: ${pnl_amount:.2f})")
    
    db.commit()
    db.commit()
    return created_entries


def seed_trades(db, count=20):
    """Create sample closed trades for strategy performance."""
    print(f"\n🤖 Creating {count} test strategy trades...")
    
    strategies = ["MTF Momentum", "SMC Reversal", "News Sentiment"]
    symbols = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    
    created_trades = []
    
    for i in range(count):
        strategy = random.choice(strategies)
        symbol = random.choice(symbols)
        direction = random.choice(list(TradeDirection))
        is_winner = random.random() > 0.45 
        
        entry_price = random.uniform(1800, 2100) if "XAU" in symbol else random.uniform(1.0, 1.2)
        if "BTC" in symbol: entry_price = random.uniform(40000, 70000)
            
        pnl = random.uniform(50, 200) if is_winner else -random.uniform(10, 50)
        
        trade = Trade(
            trade_id=uuid.uuid4(),
            symbol=symbol,
            strategy_name=strategy,
            signal_timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            status=TradeStatus.CLOSED,
            direction=direction,
            entry_price=entry_price,
            exit_price=entry_price + (10 if is_winner else -5), # Dummy logic
            sl_price=entry_price * 0.99,
            tp_price=entry_price * 1.02,
            lot_size=0.1,
            risk_usd=10.0,
            pnl_usd=pnl,
            exit_timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        )
        
        db.add(trade)
        created_trades.append(trade)
        
    db.commit()
    print(f"  ✓ Created {len(created_trades)} trades across {len(strategies)} strategies")
    return created_trades



def main():
    """Main seeding function."""
    print("🌱 Seeding test data for MTF Trading System...")
    
    db = SessionLocal()
    
    try:
        # Seed users
        users = seed_users(db, count=3)
        
        # Seed funds
        funds = seed_funds(db, users, count=2)
        
        # Seed journal entries
        entries = seed_journal_entries(db, users, count=15)

        # Seed strategy trades
        trades = seed_trades(db, count=50)
        
        # Summary
        print("\n" + "="*60)
        print("✅ Seeding completed successfully!")
        print("="*60)
        print(f"📊 Summary:")
        print(f"  - Users: {len(users)}")
        print(f"  - Funds: {len(funds)}")
        print(f"  - Journal Entries: {len(entries)}")
        print("\n🔑 Test Credentials:")
        print("  - Username: trader1 | Password: password123")
        print("  - Username: trader2 | Password: password123")
        print("  - Username: admin   | Password: admin123")
        print("\n💡 Next Steps:")
        print("  1. Start the backend: cd services/api-gateway && uvicorn app.main:app --reload")
        print("  2. Start the frontend: cd frontend && pnpm dev")
        print("  3. Login at: http://localhost:3000/login")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding test data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
