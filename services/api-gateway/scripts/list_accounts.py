import os
import uuid
import sys

# Add the app directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))

try:
    from app.database import SessionLocal
    from app.models.broker_account import BrokerAccount
except ImportError:
    sys.path.append('/app')
    from app.database import SessionLocal
    from app.models.broker_account import BrokerAccount

def list_accounts():
    db = SessionLocal()
    try:
        accounts = db.query(BrokerAccount).all()
        print("\n" + "="*80)
        print(f"{'ACCOUNT NAME':<30} | {'BROKER':<10} | {'UUID (broker_account_id)':<36}")
        print("-"*80)
        for acc in accounts:
            print(f"{acc.account_name:<30} | {acc.broker_name:<10} | {str(acc.id):<36}")
        print("="*80 + "\n")
    finally:
        db.close()

if __name__ == "__main__":
    list_accounts()
