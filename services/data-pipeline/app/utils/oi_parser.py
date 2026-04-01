import openpyxl
import io
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class OpenInterestParser:
    """
    Parses Open Interest Matrix Excel files using openpyxl for performance.
    """
    
    @staticmethod
    def parse(file_content: bytes, snapshot_at: Optional[datetime] = None, underlying_price: Optional[float] = None) -> Tuple[List[Dict[str, Any]], datetime]:
        """
        Parses the Excel content and returns a list of records and the snapshot timestamp.
        """
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
        sheet = wb.worksheets[0]
        
        # Determine snapshot timestamp
        if not snapshot_at:
            try:
                # Assuming sheet name is like "Tue, Oct 21, 2025" or "Fri, Feb 27, 2026"
                snapshot_at = datetime.strptime(sheet.title, "%a, %b %d, %Y")
            except ValueError as e:
                logger.warning(f"Could not parse date from sheet name '{sheet.title}': {e}. Using current time.")
                snapshot_at = datetime.utcnow()

        # Find "futures" and "strike" rows
        futures_row_idx = -1
        strike_row_idx = -1
        strike_col_idx = -1
        
        # Scan first 20 rows
        for r_idx, row in enumerate(sheet.iter_rows(max_row=20), 1):
            for c_idx, cell in enumerate(row, 1):
                val = str(cell.value).strip().lower() if cell.value is not None else ""
                if val == "futures":
                    futures_row_idx = r_idx
                elif val == "strike":
                    strike_row_idx = r_idx
                    strike_col_idx = c_idx
            if strike_row_idx != -1:
                break
                
        if strike_row_idx == -1:
            raise ValueError("Could not find 'Strike' column in Excel file.")

        # If futures row not found specifically, assume it's right above strike row
        if futures_row_idx == -1 and strike_row_idx > 1:
            futures_row_idx = strike_row_idx - 1

        # Parse Headers
        futures_row = list(sheet.iter_rows(min_row=futures_row_idx, max_row=futures_row_idx, values_only=True))[0]
        strike_row = list(sheet.iter_rows(min_row=strike_row_idx, max_row=strike_row_idx, values_only=True))[0]
        sub_header_row = list(sheet.iter_rows(min_row=strike_row_idx + 1, max_row=strike_row_idx + 1, values_only=True))[0]
        
        col_map = OpenInterestParser._map_columns_v2(futures_row, strike_row, sub_header_row, strike_col_idx)

        # Extract Records
        records = []
        # Data starts after sub-header
        for row in sheet.iter_rows(min_row=strike_row_idx + 2, values_only=True):
            strike_val = row[strike_col_idx - 1] # 0-indexed
            try:
                if strike_val is None: continue
                strike = float(strike_val)
            except:
                continue
            
            row_data = OpenInterestParser._process_row(row, col_map)
            
            for symbol, data in row_data.items():
                # Determine if we need to apply scaling (e.g. Gold 2x basis correction)
                is_gold = any(s in symbol.upper() for s in ["OG", "GC", "XAU"])
                
                final_strike = strike
                final_underlying = (data['underlying_price'] or underlying_price)

                records.append({
                    'snapshot_at': snapshot_at,
                    'contract_symbol': symbol,
                    'underlying_contract_symbol': data['underlying_symbol'],
                    'dte': data['dte'],
                    'strike': final_strike,
                    'call_oi': data['call'],
                    'put_oi': data['put'],
                    'underlying_price': final_underlying,
                    'created_at': datetime.utcnow()
                })
                
        return records, snapshot_at

    @staticmethod
    def _map_columns_v2(futures_row: List[Any], strike_row: List[Any], sub_header_row: List[Any], strike_col_idx: int) -> Dict[int, Dict[str, Any]]:
        col_map = {}
        strike_0_idx = strike_col_idx - 1
        
        current_underlying_symbol = None
        current_underlying_price = None
        current_contract = None
        current_dte = 0
        
        for col_idx in range(len(strike_row)):
            if col_idx == strike_0_idx:
                continue
            
            f_val = str(futures_row[col_idx]).strip() if col_idx < len(futures_row) and futures_row[col_idx] is not None else ""
            s_val = str(strike_row[col_idx]).strip() if col_idx < len(strike_row) and strike_row[col_idx] is not None else ""
            sh_val = str(sub_header_row[col_idx]).strip() if col_idx < len(sub_header_row) and sub_header_row[col_idx] is not None else ""

            # Update underlying info from futures row (e.g., "GCJ6\n5361.2")
            if f_val and f_val.lower() != 'futures':
                f_lines = f_val.split('\n')
                current_underlying_symbol = f_lines[0].strip()
                if len(f_lines) > 1:
                    try:
                        current_underlying_price = float(f_lines[1].strip())
                    except:
                        pass

            # Update option info from strike row (e.g., "OGJ6\n25 DTE")
            if s_val and s_val.lower() != 'strike':
                s_lines = s_val.split('\n')
                current_contract = s_lines[0].strip()
                if len(s_lines) > 1:
                    match = re.search(r"(\d+)\s*DTE", s_lines[1], re.IGNORECASE)
                    if match:
                        current_dte = int(match.group(1))
                    else:
                        current_dte = 0
                else:
                    # Fallback or if already set
                    pass

            if current_contract and sh_val in ['C', 'P']:
                col_map[col_idx] = {
                    'symbol': current_contract,
                    'underlying_symbol': current_underlying_symbol,
                    'underlying_price': current_underlying_price,
                    'dte': current_dte,
                    'type': sh_val
                }
        return col_map

    @staticmethod
    def _process_row(row: List[Any], col_map: Dict[int, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        row_data = {}
        for col_idx, info in col_map.items():
            val = row[col_idx]
            if val is None or str(val).strip() == '-':
                val = 0
            else:
                try:
                    val = float(val)
                except:
                    val = 0
            
            key = info['symbol']
            if key not in row_data:
                row_data[key] = {
                    'underlying_symbol': info['underlying_symbol'],
                    'underlying_price': info['underlying_price'],
                    'dte': info['dte'], 
                    'call': 0, 
                    'put': 0
                }
            
            if info['type'] == 'C':
                row_data[key]['call'] = val
            elif info['type'] == 'P':
                row_data[key]['put'] = val
                
        return row_data
