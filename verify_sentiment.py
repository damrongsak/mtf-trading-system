import json
import urllib.request
import time
import subprocess
import json

def fetch_cached_sentiment():
    print("--- 1. Testing GET /api/v1/analysis/sentiment/cached ---")
    try:
        url = "http://localhost:8000/api/v1/analysis/sentiment/cached?symbol=XAUUSD"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("Response:", json.dumps(data, indent=2))
            return data
    except Exception as e:
        print("Error fetching cached sentiment:", e)
        return None

def trigger_sentiment_analysis():
    print("\n--- 2. Triggering POST /api/v1/analysis/analyze/sentiment (ai-analyst) ---")
    # ai-analyst internal port is 8000, but from host it might be 8003 or we can use docker exec
    # Let's use docker exec to run a small command inside the ai-analyst container
    cmd = [
        "docker", "compose", "exec", "ai-analyst", 
        "python", "-c", 
        "import asyncio; from app.services.sentiment import SentimentService; "
        "async def run(): svc = SentimentService(); res = await svc.get_sentiment('XAUUSD'); print(res); await svc.close(); "
        "asyncio.run(run())"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/dan/workspace/mtf-trading-system")
        if result.returncode == 0:
            print("Successfully executed sentiment generation script inside ai-analyst:")
            print(result.stdout)
        else:
            print("Failed to run script inside ai-analyst:")
            print(result.stderr)
    except Exception as e:
        print("Error triggering AI Analyst:", e)

def fetch_logs():
    print("\n--- 3. Fetching recent logs from ai-analyst related to sentiment ---")
    cmd = ["docker", "compose", "logs", "--tail", "50", "ai-analyst"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/dan/workspace/mtf-trading-system")
        logs = result.stdout.split('\n')
        sentiment_logs = [l for l in logs if "sentiment" in l.lower() or "cache" in l.lower()]
        for log in sentiment_logs[-10:]:
            print(log.strip())
    except Exception as e:
        print("Error fetching logs:", e)

if __name__ == "__main__":
    initial_data = fetch_cached_sentiment()
    trigger_sentiment_analysis()
    time.sleep(1) # wait for redis propagation
    final_data = fetch_cached_sentiment()
    fetch_logs()
