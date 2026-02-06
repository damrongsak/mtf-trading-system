import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())

from app.services.news_service import NewsService
from app.database import SessionLocal
from app.schemas import SentimentCreate

def verify_trend():
    print("--- Verifying Trend Analysis Endpoint ---")
    db = SessionLocal()
    
    try:
        # 1. Insert Dummy Sentiment
        print("[1] Inserting dummy sentiment...")
        dummy = SentimentCreate(
            symbol="TEST_TREND",
            score=0.75,
            reason="Market is looking bullish due to verifies.",
            source_breakdown={"SourceA": 0.8}
        )
        saved = NewsService.save_sentiment(db, dummy)
        print(f"Saved ID: {saved.id}")
        
        # 2. Retrieve History (No filters)
        print("\n[2] Retrieving History (All)...")
        history = NewsService.get_sentiment_history(db, symbol="TEST_TREND")
        print(f"Count: {len(history)}")
        if len(history) > 0:
            print(f"Latest: {history[0].score} ({history[0].created_at})")
            
        # 3. Retrieve History (Date Filter)
        print("\n[3] Retrieving History (Date Filter)...")
        results = NewsService.get_sentiment_history(
            db, 
            symbol="TEST_TREND", 
            start_date=datetime(2025, 1, 1),
            end_date=datetime.utcnow()
        )
        print(f"Count (Filtered): {len(results)}")
        
        if len(history) == len(results):
             print("\nSUCCESS: Trend retrieval working.")
        else:
             print("\nWARNING: Counts mismatch or filtering issue.")
             
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_trend()
