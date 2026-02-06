#!/usr/bin/env python3
import argparse
import requests
import json
import sys
from datetime import datetime
from typing import Optional

# Configuration
API_URL = "http://api-gateway:8000/api/v1/news"

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║             MTF OLYMPUS - SENTIMENT ENGINE CLI             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

def analyze_sentiment(symbol: str, context: str = "Market Analysis"):
    print(f"{Colors.CYAN}Generating Analysis for {symbol}... (This may take 10-20s){Colors.ENDC}")
    try:
        url = f"{API_URL}/analyze"
        payload = {"symbol": symbol, "context": context}
        resp = requests.post(url, json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            score = data.get('score', 0)
            reason = data.get('reason', 'No reason provided')
            
            # Colorize Score
            score_color = Colors.GREEN if score > 0 else (Colors.FAIL if score < 0 else Colors.WARNING)
            sentiment_text = "BULLISH" if score > 0.3 else ("BEARISH" if score < -0.3 else "NEUTRAL")

            print(f"\n{Colors.BOLD}► Analysis Result:{Colors.ENDC}")
            print(f"  • Sentiment: {score_color}{sentiment_text} ({score}){Colors.ENDC}")
            print(f"  • Reason:    {reason}")
            print(f"  • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  • Status:    {Colors.GREEN}Saved to Database{Colors.ENDC}\n")
        else:
            print(f"{Colors.FAIL}Error: {resp.status_code} - {resp.text}{Colors.ENDC}")
            
    except Exception as e:
        print(f"{Colors.FAIL}Connection Failed: {e}{Colors.ENDC}")

def get_history(symbol: Optional[str], limit: int):
    print(f"{Colors.CYAN}Fetching History for {symbol or 'ALL'}...{Colors.ENDC}")
    try:
        url = f"{API_URL}/sentiment/history"
        params = {}
        if symbol: params['symbol'] = symbol
        
        resp = requests.get(url, params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            # Sort by date desc just in case, verify persistence
            sorted_data = sorted(data, key=lambda x: x['created_at'], reverse=True)[:limit]
            
            print(f"\n{Colors.BOLD}{'ID':<5} {'SYMBOL':<10} {'SCORE':<8} {'DATE':<25} {'REASON'}{Colors.ENDC}")
            print("-" * 120)
            
            for item in sorted_data:
                score = item['score']
                score_str = f"{score:+.2f}"
                color = Colors.GREEN if score > 0 else (Colors.FAIL if score < 0 else Colors.WARNING)
                
                reason = item['reason'] or ""
                if len(reason) > 60:
                    reason = reason[:57] + "..."
                    
                print(f"{item['id']:<5} {item['symbol']:<10} {color}{score_str:<8}{Colors.ENDC} {item['created_at']:<25} {reason}")
            print("\n")
        else:
             print(f"{Colors.FAIL}Error: {resp.status_code} - {resp.text}{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}Connection Failed: {e}{Colors.ENDC}")

def get_headlines(symbol: str):
    print(f"{Colors.CYAN}Fetching Headlines for {symbol}...{Colors.ENDC}")
    try:
        url = f"{API_URL}/headlines"
        params = {"symbol": symbol}
        resp = requests.get(url, params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n{Colors.BOLD}Recent News:{Colors.ENDC}")
            for idx, item in enumerate(data[:5], 1):
                source = item.get('source', 'Unknown')
                title = item.get('title', 'No Title')
                print(f"{idx}. [{Colors.BLUE}{source}{Colors.ENDC}] {title}")
            print("\n")
        else:
             print(f"{Colors.FAIL}Error: {resp.status_code} - {resp.text}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Connection Failed: {e}{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description="MTF Olympus Sentiment CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze Command
    analyze_parser = subparsers.add_parser("analyze", help="Trigger AI Sentiment Analysis")
    analyze_parser.add_argument("symbol", type=str, help="Market Symbol (e.g., XAU/USD)")

    # History Command
    history_parser = subparsers.add_parser("history", help="View Sentiment History")
    history_parser.add_argument("--symbol", type=str, help="Filter by Symbol")
    history_parser.add_argument("--limit", type=int, default=10, help="Limit results")

    # Headlines Command
    news_parser = subparsers.add_parser("news", help="View Raw News Headlines")
    news_parser.add_argument("symbol", type=str, help="Market Symbol")

    args = parser.parse_args()

    print_header()

    if args.command == "analyze":
        analyze_sentiment(args.symbol)
    elif args.command == "history":
        get_history(args.symbol, args.limit)
    elif args.command == "news":
        get_headlines(args.symbol)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
