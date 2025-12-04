"""
Import cTrader trading history Excel into journal entries
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis, GameLevel
from app.models.user_fund import User

def parse_ctrader_excel(excel_path: str):
    """Parse cTrader Excel file and extract trade data"""
    print(f"📊 Reading Excel file: {excel_path}")
    
    # Read Excel file
    df = pd.read_excel(excel_path, engine='openpyxl')
    
    print(f"✅ Found {len(df)} rows")
    print(f"📋 Columns: {', '.join(df.columns.tolist())}")
    
    trades = []
    
    for idx, row in df.iterrows():
        try:
            # Extract trade data
            symbol = str(row.get('Symbol', 'XAU/USD')).replace("XAUUSD", "XAU/USD")
            direction = "LONG" if str(row.get('Opening direction', 'Buy')).lower() == 'buy' else "SHORT"
            
            # Parse timestamps - use actual column names
            opening_time = pd.to_datetime(row['Opening time'])
            closing_time = pd.to_datetime(row['Closing time'])
            
            # Prices and PnL
            entry_price = float(row['Entry price'])
            exit_price = float(row['Closing price'])
            net_pnl = float(row['Net $'])
            pips = float(row.get('Pips', 0))
            
            # Comment
            comment = str(row.get('Comment', ''))
            
            # Determine session based on time (UTC+7)
            hour = opening_time.hour
            if 1 <= hour < 9:
                session = "ASIAN"
            elif 9 <= hour < 13:
                session = "LONDON"
            elif 13 <= hour < 21:
                session = "NY"
            else:
                session = "ASIAN"
            
            # Determine game level based on PnL
            if net_pnl > 20:
                game_level = GameLevel.A_GAME
            elif net_pnl > 5:
                game_level = GameLevel.B_GAME
            else:
                game_level = GameLevel.C_GAME
            
            trades.append({
                'symbol': symbol,
                'direction': direction,
                'opening_time': opening_time,
                'closing_time': closing_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'net_pnl': net_pnl,
                'pips': pips,
                'session': session,
                'game_level': game_level,
                'comment': comment,
                'is_stopout': 'Stop-Out' in comment
            })
        except Exception as e:
            print(f"⚠️  Warning: Failed to parse row {idx}: {e}")
            continue
    
    return trades

def import_to_journal(db: Session, trades: list, username: str):
    """Import trades to journal entries"""
    # Get user
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"❌ Error: User '{username}' not found")
        return 0
    
    created_count = 0
    skipped_count = 0
    
    for trade in trades:
        # Check if already exists (by approximate timestamp and symbol)
        existing = db.query(JournalEntry).filter(
            JournalEntry.user_id == user.id,
            JournalEntry.symbol == trade['symbol'],
            JournalEntry.pnl_amount == trade['net_pnl']
        ).first()
        
        if existing:
            skipped_count += 1
            continue
        
        # Create journal entry
        entry = JournalEntry(
            user_id=user.id,
            symbol=trade['symbol'],
            direction=trade['direction'],
            entry_price=trade['entry_price'],
            exit_price=trade['exit_price'],
            pnl_amount=trade['net_pnl'],
            pnl_r=None,  # Not available from cTrader
            risk_amount=None,  # Not available
            stop_loss_price=None,  # Not available
            take_profit_price=None,  # Not available
            session=trade['session'],
            context_score=5 if not trade['is_stopout'] else 2,  # Default scoring
            game_level=trade['game_level'],
            created_at=trade['closing_time'],
            updated_at=trade['closing_time']
        )
        db.add(entry)
        db.flush()
        
        # Add mental state
        mental = MentalState(
            journal_entry_id=entry.id,
            greed_level=7 if trade['net_pnl'] > 0 else 3,
            fear_level=3 if trade['net_pnl'] > 0 else 7,
            tilt_level=8 if trade['is_stopout'] else 2,
            confidence_level=6 if trade['net_pnl'] > 0 else 3,
            discipline_level=3 if trade['is_stopout'] else 6
        )
        db.add(mental)
        
        # Add timeline events
        events = [
            TimelineEvent(
                journal_entry_id=entry.id,
                type="ENTRY",
                description=f"Opened {trade['direction']} at {trade['entry_price']}",
                order_index=1
            ),
            TimelineEvent(
                journal_entry_id=entry.id,
                type="EXIT",
                description=f"Closed at {trade['exit_price']} ({'+' if trade['net_pnl'] > 0 else ''}{trade['net_pnl']:.2f} USD, {trade['pips']:.0f} pips)",
                order_index=2
            )
        ]
        for event in events:
            db.add(event)
        
        # Add root cause if stop-out
        if trade['is_stopout']:
            root_cause = RootCauseAnalysis(
                journal_entry_id=entry.id,
                problem="Stop-out occurred",
                why_exist="Poor risk management or overleveraging",
                flaw="Insufficient margin or no stop loss",
                correction="Implement strict risk management rules",
                logic="Never risk more than 1-2% per trade, maintain adequate margin"
            )
            db.add(root_cause)
        
        created_count += 1
        
        if created_count % 10 == 0:
            print(f"  📝 Imported {created_count} trades...")
    
    db.commit()
    print(f"\n✅ Successfully imported {created_count} trades")
    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} duplicate trades")
    
    return created_count

def main():
    if len(sys.argv) < 3:
        print("Usage: python import_ctrader_excel.py <excel_file_path> <username>")
        print("Example: python import_ctrader_excel.py ../../example/cT_6023410_2025-12-04_12-41.xlsx trader1")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    username = sys.argv[2]
    
    if not Path(excel_path).exists():
        print(f"❌ Error: File not found: {excel_path}")
        sys.exit(1)
    
    print(f"📄 Parsing cTrader Excel file: {excel_path}")
    trades = parse_ctrader_excel(excel_path)
    print(f"✅ Parsed {len(trades)} trades")
    
    if trades:
        print(f"\n🔄 Importing to journal for user '{username}'...")
        db = SessionLocal()
        try:
            import_to_journal(db, trades, username)
        finally:
            db.close()

if __name__ == "__main__":
    main()
