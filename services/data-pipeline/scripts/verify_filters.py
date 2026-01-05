import requests
import sys

BASE_URL = "http://localhost:8000/api/v1" # Direct to data-pipeline for now, or via gateway

def verify_filters():
    print("Fetching snapshots...")
    resp = requests.get(f"{BASE_URL}/ingest/open-interest/snapshots")
    if resp.status_code != 200:
        print(f"Failed to fetch snapshots: {resp.text}")
        return
    
    snapshots = resp.json()
    if not snapshots:
        print("No snapshots found. Please upload data first.")
        return
        
    latest_snapshot = snapshots[0]['snapshot_at']
    print(f"Using snapshot: {latest_snapshot}")
    
    # 1. Get Contracts
    print("\nFetching Contracts...")
    resp = requests.get(f"{BASE_URL}/ingest/open-interest/contracts", params={"snapshot_at": latest_snapshot})
    if resp.status_code != 200:
        print(f"Failed to fetch contracts: {resp.text}")
        return
    contracts = resp.json()
    print(f"Available contracts: {contracts}")
    
    # 2. Get Analysis (No Filters)
    print("\nFetching Analysis (No Filters)...")
    resp = requests.get(f"{BASE_URL}/ingest/open-interest/analysis", params={"snapshot_at": latest_snapshot})
    base_data = resp.json()
    base_oi = base_data['summary']['total_call_oi'] + base_data['summary']['total_put_oi']
    print(f"Base Total OI: {base_oi}")
    
    # 3. Get Analysis (Min OI Filter)
    print(f"\nFetching Analysis (Min OI > 500)...")
    resp = requests.get(f"{BASE_URL}/ingest/open-interest/analysis", params={"snapshot_at": latest_snapshot, "min_oi": 500})
    filtered_data = resp.json()
    filtered_oi = filtered_data['summary']['total_call_oi'] + filtered_data['summary']['total_put_oi']
    print(f"Filtered Total OI: {filtered_oi}")
    
    if filtered_oi < base_oi:
        print("PASS: Min OI Filter reduced total count.")
    else:
        print("WARN: Min OI Filter had no effect (maybe all strikes have > 500?)")

    # 4. Get Analysis (Contract Filter)
    if contracts:
        contract = contracts[0]
        print(f"\nFetching Analysis (Contract: {contract})...")
        resp = requests.get(f"{BASE_URL}/ingest/open-interest/analysis", params={"snapshot_at": latest_snapshot, "contract": contract})
        contract_data = resp.json()
        contract_oi = contract_data['summary']['total_call_oi'] + contract_data['summary']['total_put_oi']
        print(f"Contract Total OI: {contract_oi}")
        
        if contract_oi <= base_oi:
             print("PASS: Contract Filter returned subset.")

    # 5. Smart Filter (Std Dev)
    print("\n--- Test 5: Smart Filter (Std Dev) ---")
    # Note: 'smart_filter' param must be supported by the endpoint
    resp = requests.get(f"{BASE_URL}/ingest/open-interest/analysis", params={"snapshot_at": latest_snapshot, "smart_filter": "true"})
    
    if resp.status_code == 200:
        smart_data = resp.json()
        # We expect fewer strikes in distribution than the base analysis
        count_smart = len(smart_data.get('distribution', []))
        count_base = len(base_data.get('distribution', []))
        
        print(f"Smart Filter Rows: {count_smart} vs Base: {count_base}")
        if count_smart < count_base:
            print("✅ Smart Filter reduced row count (Optimization successful)")
        else:
            print("⚠️ Smart Filter row count same as Base (Data might be tight or filter loose)")
            
        # Print Range
        if count_smart > 0:
            strikes = [d['strike'] for d in smart_data['distribution']]
            print(f"Smart Range: {min(strikes)} -> {max(strikes)}")
    else:
        print(f"❌ Smart Filter request failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    verify_filters()
