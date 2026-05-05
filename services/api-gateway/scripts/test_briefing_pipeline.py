
import requests
import time
import json
import os

API_BASE = "http://localhost:8000/api/v1/ai/think"
TOKEN = os.getenv("TEST_AUTH_TOKEN", "test-token") # Replace with real token if needed

def test_briefing_pipeline():
    print("🚀 Starting AI Briefing Pipeline Test (via /think)...")
    start_time = time.time()
    
    payload = {
        "message": "Get me the daily briefing for gold",
        "user_id": "test_user_001"
    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Increase timeout to 125s to avoid script-side timeout
        response = requests.post(API_BASE, json=payload, headers=headers, timeout=125)
        latency = time.time() - start_time
        
        print(f"⏱️ Latency: {latency:.2f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            content = data.get("response", "")
            intent = data.get("intent", "UNKNOWN")
            
            print(f"✅ Success! Response received. (Intent: {intent})")
            
            # Check for hardness override evidence
            if intent == "DAILY_BRIEFING":
                 print("⭐ Hardness Override confirmed: Intent correctly forced to DAILY_BRIEFING.")
            else:
                 print(f"⚠️ Intent was not forced. Got: {intent}")

            if "briefing" in content.lower() or "gold" in content.lower() or len(content) > 100:
                 print("⭐ Response contains expected briefing content.")
            else:
                 print("⚠️ Response content seems too short or mismatched.")
        else:
            print(f"❌ Failed: {response.text}")
            
    except requests.exceptions.Timeout:
        print("🔴 ERROR: Request timed out after 125s!")
    except Exception as e:
        print(f"🔴 ERROR: {str(e)}")

if __name__ == "__main__":
    test_briefing_pipeline()
