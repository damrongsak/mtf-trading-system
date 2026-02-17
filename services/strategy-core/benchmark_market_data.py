
import time
import random
from datetime import datetime
from app.market_data import market_data_manager

def run_benchmark():
    symbol = "XAUUSD"
    count = 10000
    
    print(f"Benchmarking SharedMarketDataManager with {count} ticks...")
    
    # Warmup
    market_data_manager.update_tick(symbol, 2000.0, datetime.now())
    
    start_time = time.time()
    
    base_price = 2000.0
    for i in range(count):
        price = base_price + (i * 0.01)
        ts = datetime.now()
        market_data_manager.update_tick(symbol, price, ts)
        
    end_time = time.time()
    duration = end_time - start_time
    
    avg_latency_us = (duration / count) * 1_000_000
    ticks_per_sec = count / duration
    
    print(f"Total Time: {duration:.4f}s")
    print(f"Avg Latency: {avg_latency_us:.2f} microseconds per tick")
    print(f"Throughput: {ticks_per_sec:.2f} ticks/s")
    
    if avg_latency_us < 1000:
        print("✅ PASSED: Latency < 1ms")
    else:
        print("❌ FAILED: Latency > 1ms")

if __name__ == "__main__":
    run_benchmark()
