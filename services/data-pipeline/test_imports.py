import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

print("Testing imports for StreamManager...")
try:
    from app.streaming.manager import stream_manager
    print("SUCCESS: StreamManager imported.")
    
    from app.streaming.adapters.oanda import OandaStreamer
    print("SUCCESS: OandaStreamer imported.")
    
    from app.streaming.adapters.ctrader import CTraderStreamer
    print("SUCCESS: CTraderStreamer imported.")
    
    from app.scheduler.jobs import run_ingestion_job
    print("SUCCESS: run_ingestion_job imported.")

except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All imports OK.")
