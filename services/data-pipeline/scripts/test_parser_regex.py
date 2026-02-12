
import io
import re
import openpyxl
from datetime import datetime

class MockParser:
    @staticmethod
    def _map_columns(header_row, sub_header_row, strike_col_idx):
        col_map = {}
        strike_0_idx = strike_col_idx - 1
        current_contract = None
        current_dte = 0
        
        print("Debugging Column Mapping:")
        for col_idx, (header_val, sub_header_val) in enumerate(zip(header_row, sub_header_row)):
            if col_idx == strike_0_idx: continue
            
            h_val = str(header_val).strip() if header_val is not None else ""
            sh_val = str(sub_header_val).strip() if sub_header_val is not None else ""
            
            if h_val:
                print(f"  Col {col_idx}: Header='{h_val}'")
                # Regex from original code
                match = re.search(r"([A-Z0-9]+)[\s\n\r]*(\d+)\s*DTE", h_val, re.IGNORECASE)
                if match:
                    current_contract = match.group(1)
                    current_dte = int(match.group(2))
                    print(f"    -> Match! Contract='{current_contract}', DTE={current_dte}")
                else:
                    current_contract = h_val
                    current_dte = 0
                    print(f"    -> No Match. Contract='{current_contract}', DTE=0")
            
            if current_contract and sh_val in ['C', 'P']:
                print(f"    -> Mapped Col {col_idx} to {current_contract} ({sh_val})")
                col_map[col_idx] = {
                    'symbol': current_contract,
                    'dte': current_dte,
                    'type': sh_val
                }
        return col_map

# Simulate headers that might fail the regex
# Case 1: Standard (Should work)
headers_1 = ["Strike", "GCZ5 25 DTE", "GCZ5 25 DTE", "GCG6 55 DTE", "GCG6 55 DTE"]
sub_1 = ["", "C", "P", "C", "P"]

# Case 2: Different format (e.g. just "GCZ5")
headers_2 = ["Strike", "GCZ5", "GCZ5", "GCG6", "GCG6"]
sub_2 = ["", "C", "P", "C", "P"]

# Case 3: With extra spaces or newlines
headers_3 = ["Strike", "GCZ5 \n 25 DTE", "GCZ5 \n 25 DTE", "GCG6 55DTE", "GCG6 55DTE"]
sub_3 = ["", "C", "P", "C", "P"]

print("\n--- TEST CASE 1: Standard ---")
MockParser._map_columns(headers_1, sub_1, 1)

print("\n--- TEST CASE 2: No DTE ---")
MockParser._map_columns(headers_2, sub_2, 1)

print("\n--- TEST CASE 3: Newlines/Variations ---")
MockParser._map_columns(headers_3, sub_3, 1)
