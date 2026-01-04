
from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

def check_active_symbols():
    db = SessionLocal()
    try:
        print(f"{'Symbol':<15} {'Broker':<10} {'Active':<8} {'Display Name':<20}")
        print("-" * 60)
        
        # Query Active Symbols
        results = db.query(MarketSymbol).join(DataSource).filter(MarketSymbol.is_active == True).all()
        
        for ms in results:
            broker_name = ms.data_source.name if ms.data_source else "N/A"
            print(f"{ms.symbol:<15} {broker_name:<10} {str(ms.is_active):<8} {ms.display_name or ''}")
            
        print("-" * 60)
        print(f"Total Active Symbols: {len(results)}")
        
    except Exception as e:
        print(f"Error checking symbols: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_active_symbols()
