import redis
import os
import time
import sys

def watch_traces():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        print("🚀 MTF Olympus: HFT-lite Latency Trace Monitor")
        print("Listening for new traces... (Ctrl+C to stop)\n")
        
        # We can use PSUBSCRIBE if we have a channel, or just poll keys
        # But for new traces, we use a dedicated stream or just list newest keys
        # For this tool, we'll monitor the 'trace:*' keys via SCAN or a 'active_traces' set
        
        last_seen = set()
        
        while True:
            # Better approach: OrderService could also push to a channel 'execution:traces'
            # For now, let's scan.
            keys = r.keys("trace:*")
            for k in keys:
                if k not in last_seen:
                    steps = r.lrange(k, 0, -1)
                    if steps:
                        print(f"📦 Order Trace: {k.split(':')[1]}")
                        total_ms = 0
                        for s in steps:
                            name, val = s.split(":")
                            val_f = float(val[:-2])
                            print(f"  ├─ {name.ljust(25)} : {val_f:>7.2f} ms")
                            # Simple logic: the last step isn't necessarily the total
                            # but we can track the max val
                            total_ms = max(total_ms, val_f)
                        print(f"  └─ TOTAL LATENCY {''.ljust(15)} : {total_ms:>7.2f} ms\n")
                        last_seen.add(k)
            
            # Keep set size manageable
            if len(last_seen) > 100:
                last_seen = set(list(last_seen)[-50:])
                
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    watch_traces()
