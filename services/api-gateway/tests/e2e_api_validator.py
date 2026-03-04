import requests
import hmac
import hashlib
import time
import json
import sys

BASE_URL = "http://localhost:8000"
EXTERNAL_URL = f"{BASE_URL}/api/v1/external"
USER = "trader1"
PASS = "password123"

def sign_request(secret, method, path, timestamp, body=""):
    message = f"{timestamp}{method}{path}{body}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def run_e2e():
    print(f"🚀 Starting E2E Validation for {USER}...")
    
    # 1. Login
    print("\n[Step 1] Authenticating...")
    login_res = requests.post(f"{BASE_URL}/api/v1/auth/token", data={
        "username": USER,
        "password": PASS
    })
    if login_res.status_code != 200:
        print(f"❌ Login failed: {login_res.text}")
        return
    
    token = login_res.json()["auth"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authenticated.")

    # 2. Create API Key
    print("\n[Step 2] Creating API Key...")
    create_res = requests.post(f"{BASE_URL}/api/v1/api-keys", 
                              json={"name": "E2E-Validation-Key"},
                              headers=headers)
    
    if create_res.status_code != 200:
        print(f"❌ Key creation failed: {create_res.status_code} - {create_res.text}")
        return
    
    key_data = create_res.json()
    api_key = key_data["api_key"]
    api_secret = key_data["api_secret"]
    key_id = key_data["id"]
    print(f"✅ Key Created: {api_key}")
    print(f"✅ Secret Captured (First time only): {api_secret[:4]}***")

    # 3. Test HMAC Authorization
    print("\n[Step 3] Testing HMAC Auth (Valid Request)...")
    ts = str(int(time.time()))
    path = "/api/v1/external/market/snapshot/XAUUSD"
    sig = sign_request(api_secret, "GET", path, ts)
    
    ext_headers = {
        "X-API-KEY": api_key,
        "X-SIGNATURE": sig,
        "X-TIMESTAMP": ts
    }
    
    snap_res = requests.get(f"{BASE_URL}{path}", headers=ext_headers)
    if snap_res.status_code == 200:
        print(f"✅ Request Authorized! Data: {snap_res.json()['data'].get('bid')} / {snap_res.json()['data'].get('ask')}")
    else:
        print(f"❌ Request Denied: {snap_res.status_code} - {snap_res.text}")

    # 4. Test Invalid Signature
    print("\n[Step 4] Testing Security Hardening (Invalid Signature)...")
    bad_headers = ext_headers.copy()
    bad_headers["X-SIGNATURE"] = "invalid_sig"
    bad_res = requests.get(f"{BASE_URL}{path}", headers=bad_headers)
    if bad_res.status_code == 401:
        print("✅ Correctly rejected invalid signature (401).")
    else:
        print(f"❌ Security Hole! Accepted invalid signature: {bad_res.status_code}")

    # 5. Test Rate Limiting
    print("\n[Step 5] Testing Rate Limiting (10 rps)...")
    success_count = 0
    limited_count = 0
    for i in range(15):
        ts = str(int(time.time()))
        sig = sign_request(api_secret, "GET", path, ts)
        ext_headers["X-SIGNATURE"] = sig
        ext_headers["X-TIMESTAMP"] = ts
        
        res = requests.get(f"{BASE_URL}{path}", headers=ext_headers)
        if res.status_code == 200:
            success_count += 1
        elif res.status_code == 429:
            limited_count += 1
        
        if success_count + limited_count >= 15: break

    print(f"📊 Results: {success_count} Success, {limited_count} Rate Limited.")
    if limited_count > 0:
        print("✅ Rate limiting is active.")
    else:
        print("⚠️ Rate limiting not triggered. (Check if you are running too slow or limit is higher)")

    # 6. Cleanup (Revoke Key)
    print("\n[Step 6] Revoking API Key...")
    del_res = requests.delete(f"{BASE_URL}/api/v1/api-keys/{key_id}/", headers=headers)
    if del_res.status_code == 200:
        print("✅ Key revoked.")
    else:
        print(f"❌ Failed to revoke key: {del_res.status_code} - {del_res.text}")

    print("\n✨ E2E Validation Complete.")

if __name__ == "__main__":
    run_e2e()
