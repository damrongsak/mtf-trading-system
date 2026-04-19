import requests
import json
import pandas as pd

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

def evaluate_setup():
    token = authenticate("demo1", "password123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get Live Spot
    tick_resp = requests.get(f"{API_BASE_URL}/data/tick/XAUUSD", headers=headers)
    spot = tick_resp.json()["data"]["bid"]
    
    # 2. Get Latest Snapshot for snap_at
    snap_resp = requests.get(f"{API_BASE_URL}/data/open-interest/snapshots", params={"limit": 1}, headers=headers)
    snapshot = snap_resp.json()["data"][0]
    snapshot_at = snapshot["snapshot_at"]
    
    # 3. Get GEX Data
    gex_resp = requests.get(f"{API_BASE_URL}/data/open-interest/gex", params={
        "snapshot_at": snapshot_at,
        "spot_price": spot
    }, headers=headers)
    gex_data = gex_resp.json()["data"]
    
    dist = pd.DataFrame(gex_data["distribution"])
    # Sort by total GEX significance
    dist['abs_net_gex'] = dist['net_gex'].abs()
    top_levels = dist.sort_values('abs_net_gex', ascending=False)
    
    # Gamma Flip
    flip = gex_data["gamma_flip"]
    regime = gex_data["regime"]
    
    # 4. Find immediate walls
    res_walls = top_levels[top_levels['strike'] > spot].head(3)
    sup_walls = top_levels[top_levels['strike'] < spot].head(3)
    
    evaluation = {
        "snapshot_at": snapshot_at,
        "spot": spot,
        "regime": regime,
        "gamma_flip": flip,
        "resistance_walls": res_walls[['strike', 'net_gex']].to_dict('records'),
        "support_walls": sup_walls[['strike', 'net_gex']].to_dict('records')
    }
    
    return evaluation

if __name__ == "__main__":
    try:
        res = evaluate_setup()
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
