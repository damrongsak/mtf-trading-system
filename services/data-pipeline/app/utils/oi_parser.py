import pandas as pd
import io
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class OpenInterestParser:
    """
    Parses Open Interest Matrix Excel files.
    """
    
    @staticmethod
    def parse(file_content: bytes, snapshot_at: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], datetime]:
        """
        Parses the Excel content and returns a list of records and the snapshot timestamp.
        """
        xls = pd.ExcelFile(io.BytesIO(file_content))
        sheet_name = xls.sheet_names[0]
        
        # Determine snapshot timestamp
        if not snapshot_at:
            try:
                snapshot_at = datetime.strptime(sheet_name, "%a, %b %d, %Y")
            except ValueError:
                snapshot_at = datetime.utcnow()

        # Find Header Row
        header_row_idx, strike_col_idx = OpenInterestParser._find_header_row(xls, sheet_name)
        if header_row_idx == -1:
            raise ValueError("Could not find 'Strike' column in Excel file.")

        # Read Data
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=header_row_idx)
        
        # Re-verify strike column index in new df
        strike_col_idx = OpenInterestParser._find_strike_col_index(df)
        if strike_col_idx == -1:
             raise ValueError("Could not verify 'Strike' column after adjustment.")

        # Parse Columns
        col_map = OpenInterestParser._map_columns(df, strike_col_idx)

        # Extract Records
        records = []
        for idx, row in df.iterrows():
            if idx < 2: continue # Skip headers
            
            strike_val = row[strike_col_idx]
            try:
                strike = float(strike_val)
                if pd.isna(strike): continue
            except:
                continue
            
            row_data = OpenInterestParser._process_row(row, col_map)
            
            for (symbol, _), data in row_data.items():
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
    def _find_header_row(xls: pd.ExcelFile, sheet_name: str) -> Tuple[int, int]:
        preview_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=20)
        for r in range(preview_df.shape[0]):
            for c in range(preview_df.shape[1]):
                val = str(preview_df.iloc[r, c]).strip()
                if val.lower() == "strike":
                    return r, c
        return -1, -1

    @staticmethod
    def _find_strike_col_index(df: pd.DataFrame) -> int:
        for c in range(df.shape[1]):
            if str(df.iloc[0,c]).strip().lower() == "strike":
                return c
        return -1

    @staticmethod
    def _map_columns(df: pd.DataFrame, strike_col_idx: int) -> Dict[int, Dict[str, Any]]:
        col_map = {}
        for col in range(df.shape[1]):
            if col == strike_col_idx:
                continue
            
            header_val = str(df.iloc[0, col]).strip()
            sub_header_val = str(df.iloc[1, col]).strip()
            
            # Handle Merged Headers (Contract Name)
            contract_header = header_val
            if contract_header == "nan":
                temp_col = col - 1
                while temp_col >= 0:
                    val = str(df.iloc[0, temp_col]).strip()
                    if val != "nan":
                        contract_header = val
                        break
                    temp_col -= 1
            
            if contract_header == "nan": 
                continue

            current_contract = None
            current_dte = 0
            
            match = re.search(r"([A-Z0-9]+)\s*[\n\r]*\s*(\d+)\s*DTE", contract_header, re.IGNORECASE)
            if match:
                current_contract = match.group(1)
                current_dte = int(match.group(2))
            else:
                current_contract = contract_header
            
            if current_contract and sub_header_val in ['C', 'P']:
                col_map[col] = {
                    'symbol': current_contract,
                    'dte': current_dte,
                    'type': sub_header_val
                }
        return col_map

    @staticmethod
    def _process_row(row: pd.Series, col_map: Dict[int, Dict[str, Any]]) -> Dict[Tuple[str, float], Dict[str, Any]]:
        row_data = {}
        for col, info in col_map.items():
            val = row[col]
            if pd.isna(val) or str(val).strip() == '-':
                val = 0
            else:
                try:
                    val = float(val)
                except:
                    val = 0
            
            # We don't have strike here, key is just symbol specific to row logic in main loop
            # Actually, to group C/P, we need a key.
            # In the original logic, it used (symbol, strike) as key, but strike is from row.
            # Here we return by symbol since strike is constant for the row.
            
            key = (info['symbol'])
            if key not in row_data:
                row_data[key] = {'dte': info['dte'], 'call': 0, 'put': 0}
            
            if info['type'] == 'C':
                row_data[key]['call'] = val
            elif info['type'] == 'P':
                row_data[key]['put'] = val
                
        return row_data # Returns { 'ContractA': {'dte': 10, 'call': 100, 'put': 50}, ... }
