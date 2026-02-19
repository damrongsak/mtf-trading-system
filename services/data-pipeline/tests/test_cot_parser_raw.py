import pandas as pd
from app.utils.cot_parser import COTParser
import requests

def test_raw_txt_parsing():
    url = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
    print(f"Fetching data from {url}...")
    response = requests.get(url)
    content = response.content
    
    print("Parsing content...")
    records = COTParser.parse(content, symbol="GOLD")
    
    if records:
        print(f"SUCCESS: Found {len(records)} records for GOLD")
        for rec in records:
            print(f"Date: {rec['report_date']}")
            print(f"Commercials Long: {rec['commercials_long']}")
            print(f"Non-Commercials Long: {rec['non_commercials_long']}")
            print(f"Managed Money Net: {rec['managed_money_long'] - rec['managed_money_short']}")
    else:
        print("FAILED: No records found")

if __name__ == "__main__":
    test_raw_txt_parsing()
