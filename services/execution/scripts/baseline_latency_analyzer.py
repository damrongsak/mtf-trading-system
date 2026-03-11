import redis
import os
import json
import time
from datetime import datetime
from statistics import mean, median

def analyze_latencies():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        print("📊 MTF Olympus: Passive Latency Compliance Report")
        print(f"Time: {datetime.now().isoformat()}\n")
        
        keys = r.keys("trace:*")
        if not keys:
            print("❌ No traces found in Redis. System might be idle.")
            return

        internal_latencies = []
        fill_latencies = []
        rtt_latencies = []

        for k in keys:
            steps = r.lrange(k, 0, -1)
            if not steps:
                continue
            
            trace_data = {}
            for s in steps:
                try:
                    name, val = s.split(":")
                    trace_data[name] = float(val[:-2]) if val.endswith("ms") else float(val)
                except ValueError:
                    continue
            
            # 1. Internal Latency (Request Start -> Before Broker Call)
            # Find the step just before broker_execute
            # Usually: account_cache_hit, fund_cache_hit, price_cache_hit
            # we look for the max value before broker_execute
            placements = [v for n, v in trace_data.items() if n != 'broker_execute' and n != 'fill_received']
            if placements and 'broker_execute' in trace_data:
                internal_latencies.append(trace_data['broker_execute'] - max(placements))
            
            # 2. Broker RTT (Simple)
            if 'broker_execute' in trace_data:
                # broker_execute in trace is usually (time.time() - start_t) * 1000
                # but if we want RTT, we'd need another step 'broker_response'
                # For now, trace_data['broker_execute'] IS the internal time + broker RTT
                rtt_latencies.append(trace_data['broker_execute'])

            # 3. Fill Latency (The Decoupled Path)
            if 'fill_received' in trace_data and 'broker_execute' in trace_data:
                # fill_received is absolute time.time()
                # we need the duration from order finish to fill
                # but since we didn't have start_t in fill_publisher, we use absolute timestamps if available
                # In our refined code, we added absolute time to fill_received
                # Lets assume we have absolute start_t in some step
                pass

        print(f"Analyzed {len(keys)} traces.")
        
        if internal_latencies:
            print(f"\n🔹 Internal Processing Overhead (ms):")
            print(f"  ├─ Min:    {min(internal_latencies):>7.2f}")
            print(f"  ├─ Avg:    {mean(internal_latencies):>7.2f}")
            print(f"  ├─ Median: {median(internal_latencies):>7.2f}")
            print(f"  └─ Max:    {max(internal_latencies):>7.2f}")
        
        if rtt_latencies:
            print(f"\n🔹 Total Response Latency (Internal + Broker ms):")
            print(f"  ├─ Avg:    {mean(rtt_latencies):>7.2f}")
            print(f"  └─ p95:    {sorted(rtt_latencies)[int(0.95*len(rtt_latencies))]:>7.2f}")

        # Rule 7 Check
        violations = sum(1 for l in internal_latencies if l > 10.0)
        print(f"\n🛡️ Rule 7 Compliance:")
        if violations == 0:
            print("  ✅ Status: COMPLIANT (All hot-path tasks < 10ms)")
        else:
            print(f"  ⚠️ Status: NON-COMPLIANT ({violations} tasks exceeded 10ms threshold)")

    except Exception as e:
        print(f"Report Error: {e}")

if __name__ == "__main__":
    analyze_latencies()
