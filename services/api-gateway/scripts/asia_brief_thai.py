
import requests
import json
import time
import os

API_GATEWAY = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc4MDYyODU0MH0.Idu2oPaNZDBc0_ePiZIqQ5k2o4Xy6-XjgOl7Gn7AUvQ"
API_URL = "http://localhost:8000"

def generate_asia_brief():
    print("🚀 Requesting Asia Session Pre-Market Brief (XAU/USD) in Thai...")
    
    payload = {
        "message": "จัดทำรายงาน Pre-Market Brief สำหรับตลาดเอเชียของ XAU/USD โดยใช้ข้อมูล Real-time ล่าสุด รวมถึง GEX, Gamma Flip และระดับ Liquidity ที่สำคัญ สรุปแผนการเทรดที่สอดคล้องกับสภาวะตลาดปัจจุบัน",
        "intent": "briefing"
    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # 1. Submit the job
        response = requests.post(f"{API_GATEWAY}/api/v1/ai/think", json=payload, headers=headers, timeout=30)
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"✅ Job accepted. ID: {job_id}")
            
            # 2. Poll for results
            max_retries = 30
            retry_interval = 5
            
            for i in range(max_retries):
                print(f"⏳ Polling status... ({i+1}/{max_retries})")
                status_resp = requests.get(f"{API_GATEWAY}/api/v1/ai/jobs/{job_id}", headers=headers)
                
                if status_resp.status_code == 200:
                    result = status_resp.json()
                    status = result.get("status")
                    
                    if status == "completed":
                        print("✨ Job completed!")
                        # The actual AI Analyst response is inside result['data']
                        data = result.get("data", {})
                        # AI Analyst response structure: {"data": {"response": "...", ...}}
                        # Wait, api-gateway might have wrapped it differently.
                        # Let's check what's in 'data'.
                        content = data.get("response", "")
                        
                        print("\n" + "="*50)
                        print("         ASIA PRE-MARKET BRIEF (XAU/USD)")
                        print("="*50 + "\n")
                        print(content)
                        print("\n" + "="*50)
                        
                        # Save to a file
                        with open("/app/scripts/asia_brief_thai_output.md", "w", encoding="utf-8") as f:
                            f.write(content)
                        return
                    
                    elif status == "error":
                        print(f"❌ Job failed with error: {result.get('error')}")
                        return
                    
                    else:
                        # Still processing
                        pass
                else:
                    print(f"⚠️ Error checking status: {status_resp.status_code}")
                
                time.sleep(retry_interval)
            
            print("🔴 Timeout waiting for job completion.")
                
        else:
            print(f"❌ Failed to submit job: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"🔴 ERROR: {str(e)}")

if __name__ == "__main__":
    generate_asia_brief()
