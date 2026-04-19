import requests
import json
from datetime import datetime
import os

API_BASE_URL = "http://api-gateway:8000/api/v1"

def authenticate(username, password):
    url = f"{API_BASE_URL}/auth/token"
    # Unified OAuth2 form login
    data = {"username": username, "password": password}
    response = requests.post(url, data=data)
    response.raise_for_status()
    res_json = response.json()
    if "auth" in res_json:
        return res_json["auth"]["access_token"]
    return res_json.get("access_token")

def get_latest_walls():
    token = authenticate("demo1", "password123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get latest snapshot
    snap_resp = requests.get(f"{API_BASE_URL}/data/open-interest/snapshots", params={"limit": 1}, headers=headers)
    snap_resp.raise_for_status()
    snapshot = snap_resp.json()["data"][0]
    snapshot_at = snapshot["snapshot_at"]
    
    # 2. Get Live Spot Price
    tick_resp = requests.get(f"{API_BASE_URL}/data/tick/XAUUSD", headers=headers)
    if tick_resp.status_code == 200:
        spot_price = tick_resp.json()["data"]["bid"]
    else:
        # Fallback to snapshot price if tick fails
        spot_price = float(snapshot.get("underlying_price", 0.0))

    # 3. Get Analysis (for OI Walls)
    analysis_resp = requests.get(f"{API_BASE_URL}/data/open-interest/analysis", params={"snapshot_at": snapshot_at}, headers=headers)
    analysis_resp.raise_for_status()
    analysis = analysis_resp.json()["data"]
    
    # 4. Get GEX (for Gamma Flip and GEX-based walls) - Passing Live Spot Price
    gex_resp = requests.get(f"{API_BASE_URL}/data/open-interest/gex", params={
        "snapshot_at": snapshot_at,
        "spot_price": spot_price
    }, headers=headers)
    gex_resp.raise_for_status()
    gex_data = gex_resp.json()["data"]
    
    # 5. Find GEX walls (max net GEX call and put strikes)
    dist = gex_data.get("distribution", [])
    call_walls = sorted([d for d in dist if d["call_gex"] > 0], key=lambda x: x["call_gex"], reverse=True)
    put_walls = sorted([d for d in dist if d["put_gex"] < 0], key=lambda x: x["put_gex"])
    
    walls = {
        "snapshot_at": snapshot_at,
        "spot_price": spot_price,
        "gamma_flip": gex_data["gamma_flip"],
        "call_wall_oi": analysis["summary"]["max_call_strike"],
        "put_wall_oi": analysis["summary"]["max_put_strike"],
        "call_wall_gex": call_walls[0]["strike"] if call_walls else None,
        "put_wall_gex": put_walls[0]["strike"] if put_walls else None,
        "gamma_regime": gex_data["regime"]
    }
    
    return walls

if __name__ == "__main__":
    try:
        result = get_latest_walls()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
