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
    def parse(file_content: bytes, snapshot_at: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], datetime]:
        """
        Parses the Excel content and returns a list of records and the snapshot timestamp.
        """
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
        sheet = wb.worksheets[0]
        
        # Determine snapshot timestamp
        if not snapshot_at:
            try:
                # Assuming sheet name is like "Tue, Oct 21, 2025"
                snapshot_at = datetime.strptime(sheet.title, "%a, %b %d, %Y")
            except ValueError as e:
                logger.warning(f"Could not parse date from sheet name '{sheet.title}': {e}. Using current time.")
                snapshot_at = datetime.utcnow()

        # Find Header Row
        header_row_idx = -1
        strike_col_idx = -1
        
        # Scan first 20 rows for "Strike"
        for r_idx, row in enumerate(sheet.iter_rows(max_row=20), 1):
            for c_idx, cell in enumerate(row, 1):
                val = str(cell.value).strip().lower() if cell.value is not None else ""
                if val == "strike":
                    header_row_idx = r_idx
                    strike_col_idx = c_idx
                    break
            if header_row_idx != -1:
                break
                
        if header_row_idx == -1:
            raise ValueError("Could not find 'Strike' column in Excel file.")

        # Parse Columns (Headers are in header_row_idx and header_row_idx + 1)
        # We need the values for all cells in those two rows
        header_row = list(sheet.iter_rows(min_row=header_row_idx, max_row=header_row_idx, values_only=True))[0]
        sub_header_row = list(sheet.iter_rows(min_row=header_row_idx + 1, max_row=header_row_idx + 1, values_only=True))[0]
        
        col_map = OpenInterestParser._map_columns(header_row, sub_header_row, strike_col_idx)

        # Extract Records
        records = []
        # Data starts after sub-header
        for row in sheet.iter_rows(min_row=header_row_idx + 2, values_only=True):
            strike_val = row[strike_col_idx - 1] # 0-indexed in values_only tuple
            try:
                if strike_val is None: continue
                strike = float(strike_val)
            except:
                continue
            
            row_data = OpenInterestParser._process_row(row, col_map)
            
            for symbol, data in row_data.items():
                records.append({
                    'snapshot_at': snapshot_at,
                    'contract_symbol': symbol,
                    'dte': data['dte'],
                    'strike': strike,
                    'call_oi': data['call'],
                    'put_oi': data['put'],
                    'created_at': datetime.utcnow()
                })
                
        return records, snapshot_at

    @staticmethod
    def _map_columns(header_row: List[Any], sub_header_row: List[Any], strike_col_idx: int) -> Dict[int, Dict[str, Any]]:
        col_map = {}
        # strike_col_idx is 1-indexed from loop
        strike_0_idx = strike_col_idx - 1
        
        current_contract = None
        current_dte = 0
        
        for col_idx, (header_val, sub_header_val) in enumerate(zip(header_row, sub_header_row)):
            if col_idx == strike_0_idx:
                continue
            
            h_val = str(header_val).strip() if header_val is not None else ""
            sh_val = str(sub_header_row[col_idx]).strip() if sub_header_row[col_idx] is not None else ""

            # Update current contract if we find a new header
            if h_val:
                match = re.search(r"([A-Z0-9]+)[\s\n\r]*(\d+)\s*DTE", h_val, re.IGNORECASE)
                if match:
                    current_contract = match.group(1)
                    current_dte = int(match.group(2))
                else:
                    current_contract = h_val
                    current_dte = 0
            
            if current_contract and sh_val in ['C', 'P']:
                col_map[col_idx] = {
                    'symbol': current_contract,
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
                row_data[key] = {'dte': info['dte'], 'call': 0, 'put': 0}
            
            if info['type'] == 'C':
                row_data[key]['call'] = val
            elif info['type'] == 'P':
                row_data[key]['put'] = val
                
        return row_data
