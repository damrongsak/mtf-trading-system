#!/usr/bin/env python3
"""
OANDA Open Interest (OI) & cTrader Position Analyzer

Fetches Open Interest (OI) from local mtf_db and superimposes active positions
from the cTrader broker via the API Gateway. This helps identify if current trade
entries are situated near significant supply (Call OI peaks) or demand (Put OI peaks) zones.

Usage:
    Must be run inside the API Gateway container:
    $ docker compose exec api-gateway python scripts/oi_position_analyzer.py

Arguments:
    --symbol        Symbol to analyze (default: XAUUSD, automatically maps to OG_GC for OI)
    --user          Gateway Username (default: demo1)
    --password      Gateway Password (default: password123)
    --gateway-url   API Gateway Base URL (default: http://localhost:8000/api/v1)

Dependencies:
    Requires `httpx` and `psycopg2` (both available in api-gateway environment).
"""
import os
import argparse
import httpx
import psycopg2

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_db_connection():
    host = os.getenv("DB_HOST", "mtf-postgres")
    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME", "mtf_db"),
            user=os.getenv("DB_USER", "trader"),
            password=os.getenv("DB_PASSWORD", "trader"),
            host=host, 
            port=os.getenv("DB_PORT", "5432"),
            connect_timeout=3
        )
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Direct DB connection failed on {host}: {e}{Colors.ENDC}")
        return None

def fetch_oi_histogram(symbol: str, min_dte: int = 0, max_dte: int = 9999):
    """
    Fetch the OI peaks from the database.
    """
    # Gold options symbol "OG_GC" aligns with "XAUUSD" spot.
    search_symbol = symbol
    if "XAU" in symbol.upper() or "GOLD" in symbol.upper():
        search_symbol = "GC%%" # Double % because of psycopg2 escaping
        
    conn = get_db_connection()
    if not conn:
        return [], []
        
    try:
        cur = conn.cursor()
        
        # Find the latest snapshot date for this symbol
        cur.execute("""
            SELECT MAX(snapshot_at) 
            FROM open_interest
            WHERE contract_symbol LIKE %s OR underlying_contract_symbol LIKE %s
        """, (search_symbol, search_symbol))
        
        max_date_row = cur.fetchone()
        if not max_date_row or not max_date_row[0]:
            print(f"{Colors.YELLOW}Warning: No snapshots found in DB for {symbol}.{Colors.ENDC}")
            return [], []
            
        latest_snapshot = max_date_row[0]
        print(f"  {Colors.CYAN}Using OI Data Snapshot: {latest_snapshot}{Colors.ENDC}")
        
        # Get Top 5 Call OI (Supply / Resistance)
        cur.execute("""
            SELECT strike, sum(call_oi) as total_call
            FROM open_interest
            WHERE (contract_symbol LIKE %s OR underlying_contract_symbol LIKE %s)
              AND snapshot_at = %s
              AND dte >= %s AND dte <= %s
            GROUP BY strike
            HAVING sum(call_oi) > 0
            ORDER BY total_call DESC
            LIMIT 5;
        """, (search_symbol, search_symbol, latest_snapshot, min_dte, max_dte))
        supply_zones = cur.fetchall()
        
        # Get Top 5 Put OI (Demand / Support)
        cur.execute("""
            SELECT strike, sum(put_oi) as total_put
            FROM open_interest
            WHERE (contract_symbol LIKE %s OR underlying_contract_symbol LIKE %s)
              AND snapshot_at = %s
              AND dte >= %s AND dte <= %s
            GROUP BY strike
            HAVING sum(put_oi) > 0
            ORDER BY total_put DESC
            LIMIT 5;
        """, (search_symbol, search_symbol, latest_snapshot, min_dte, max_dte))
        demand_zones = cur.fetchall()
        
        return supply_zones, demand_zones
    except Exception as e:
        print(f"{Colors.RED}❌ Database query failed: {e}{Colors.ENDC}")
        return [], []
    finally:
        conn.close()

def login_and_get_token(url_base, user, pwd):
    try:
        resp = httpx.post(f"{url_base}/auth/token", data={"username": user, "password": pwd}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "auth" in data and "access_token" in data["auth"]:
            return data["auth"]["access_token"]
        return data.get("access_token")
    except Exception as e:
        print(f"{Colors.RED}❌ API Login Failed: {e}{Colors.ENDC}")
        return None

def fetch_broker_account(url_base, token):
    try:
        resp = httpx.get(f"{url_base}/accounts/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        resp.raise_for_status()
        accounts = resp.json()
        if isinstance(accounts, dict) and "data" in accounts:
            accounts = accounts["data"]
        
        if accounts and len(accounts) > 0:
            # Prefer an active one
            active_accounts = [a for a in accounts if a.get('is_active')]
            if active_accounts:
                return active_accounts[0]
            return accounts[0]
        return None
    except Exception as e:
        print(f"{Colors.RED}❌ Fetch Accounts Failed for endpoint /accounts/: {e}{Colors.ENDC}")
        try:
            # Fallback to older endpoint if needed
            resp = httpx.get(f"{url_base}/api/v1/accounts/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            if resp.status_code == 200:
                accounts = resp.json()
                if isinstance(accounts, dict) and "data" in accounts:
                    accounts = accounts["data"]
                if accounts and len(accounts) > 0:
                    return accounts[0]
        except Exception:
            pass

        return None

def fetch_open_positions(url_base, token, broker_account_id):
    try:
        # According to 04_api_spec.yaml, it's a POST to /execution/trades/open
        resp = httpx.post(
            f"{url_base}/execution/trades/open", 
            json={"broker_account_id": broker_account_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
            follow_redirects=True
        )
        if resp.status_code == 307:
            # In case of strict slashes
            resp = httpx.post(
                f"{url_base}/execution/trades/open", 
                json={"broker_account_id": broker_account_id},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        print(f"{Colors.RED}❌ Fetch Open Positions Failed: {e}{Colors.ENDC}")
        return []

def print_zone_analysis(supply, demand, positions):
    print(f"\n{Colors.HEADER}{Colors.BOLD}📈 MTF OI & POSITION ANALYZER 📉{Colors.ENDC}")
    print("=" * 60)
    
    print(f"\n{Colors.RED}📉 Top Supply Zones (Resistance - Call OI Peaks){Colors.ENDC}")
    if not supply:
        print("  ⚠️ No Supply OI data available in DB for this symbol.")
    else:
        # Sort by strike descending for display (Highest strike on top just standard)
        for idx, (strike, oi) in enumerate(sorted(supply, key=lambda x: -float(x[0]))):
            print(f"  [{idx+1}] Strike: ${strike:<8.2f} | Open Interest: {oi:,.0f} contracts")
        
    print(f"\n{Colors.GREEN}📈 Top Demand Zones (Support - Put OI Peaks){Colors.ENDC}")
    if not demand:
        print("  ⚠️ No Demand OI data available in DB for this symbol.")
    else:
        # Sort by strike descending
        for idx, (strike, oi) in enumerate(sorted(demand, key=lambda x: -float(x[0]))):
            print(f"  [{idx+1}] Strike: ${strike:<8.2f} | Open Interest: {oi:,.0f} contracts")
        
    print(f"\n{Colors.CYAN}{Colors.BOLD}⚡ Current cTrader Open Positions{Colors.ENDC}")
    if not positions:
        print("  ⚠️ No active positions found on the broker.")
    else:
        for pos in positions:
            side = pos.get('direction', pos.get('side', 'UNKNOWN')).upper()
            color = Colors.GREEN if side == 'BUY' else Colors.RED
            sym = pos.get('symbol', 'UNKNOWN')
            units = pos.get('units', pos.get('volume', 0))
            price = pos.get('entry_price', pos.get('open_price', pos.get('execution_price', 0)))
            sl = pos.get('stop_loss', pos.get('sl', 'None'))
            tp = pos.get('take_profit', pos.get('tp', 'None'))
            
            print(f"  {color}{side} {sym}{Colors.ENDC} - Lots: {units/100000.0:.2f} (Base Units: {units})")
            print(f"    Entry: {price} | SL: {sl} | TP: {tp}")
            
            # Simple vicinity check
            for (strike, oi) in demand:
                if abs(float(price) - float(strike)) < 5.0: # Close to a demand strike
                    print(f"    {Colors.YELLOW}★ Entry price is near Demand Zone {strike}!{Colors.ENDC}")
            for (strike, oi) in supply:
                if abs(float(price) - float(strike)) < 5.0: # Close to a supply strike
                    print(f"    {Colors.YELLOW}★ Entry price is near Supply Zone {strike}!{Colors.ENDC}")
                    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MFT System - OI and Position Analyzer script")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Symbol to analyze")
    parser.add_argument("--user", type=str, default="demo1", help="Gateway Username")
    parser.add_argument("--password", type=str, default="password123", help="Gateway Password")
    parser.add_argument("--gateway-url", dest="gateway_url", type=str, default="http://localhost:8000/api/v1", help="API Gateway Base URL")
    parser.add_argument("--min-dte", type=int, default=0, help="Minimum Days to Expiration to include")
    parser.add_argument("--max-dte", type=int, default=9999, help="Maximum Days to Expiration to include")
    
    args = parser.parse_args()
    
    print(f"{Colors.BLUE}Fetching Open Interest histogram from database (DTE: {args.min_dte}-{args.max_dte})...{Colors.ENDC}")
    supply, demand = fetch_oi_histogram(args.symbol, args.min_dte, args.max_dte)
    
    print(f"{Colors.BLUE}Authenticating with MTF Gateway locally...{Colors.ENDC}")
    token = login_and_get_token(args.gateway_url, args.user, args.password)
    
    positions = []
    if token:
        account = fetch_broker_account(args.gateway_url, token)
        if account:
            acc_id = account.get('id')
            print(f"{Colors.BLUE}Fetching live positions for broker account '{account.get('account_name')}' (ID: {acc_id})...{Colors.ENDC}")
            positions = fetch_open_positions(args.gateway_url, token, acc_id)
        else:
            print(f"{Colors.YELLOW}No active broker accounts found for user {args.user}.{Colors.ENDC}")
    
    print_zone_analysis(supply, demand, positions)

