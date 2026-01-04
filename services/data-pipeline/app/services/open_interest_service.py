import pandas as pd
import io
import re
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.open_interest import OpenInterest
import logging

logger = logging.getLogger(__name__)

class OpenInterestService:
    @staticmethod
    def parse_and_store(
        file_content: bytes, 
        db: Session, 
        snapshot_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Parses Open Interest Matrix Excel and stores parsing results.
        """
        try:
            # Load Excel
            xls = pd.ExcelFile(io.BytesIO(file_content))
            sheet_name = xls.sheet_names[0] # Assuming first sheet
            
            # Determine snapshot timestamp
            if not snapshot_at:
                try:
                    # Try to parse sheet name like "Wed, Dec 24, 2025"
                    snapshot_at = datetime.strptime(sheet_name, "%a, %b %d, %Y")
                except ValueError:
                    snapshot_at = datetime.utcnow()
            
            # Read dataframe with header None to handle multi-row header manually
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Row 0: Contract Headers (e.g. "G5WZ5\n5 DTE")
            # Row 1: C / P
            # Row 2+: Data
            
            # Find Strike Column Index (Usually 0)
            strike_col_idx = 0
            # Verify "Strike" is in cell (0,0) or similar
            if str(df.iloc[0,0]).strip() != "Strike":
                 # Search for "Strike"
                 found = False
                 for c in range(df.shape[1]):
                     if str(df.iloc[0,c]).strip() == "Strike":
                         strike_col_idx = c
                         found = True
                         break
                 if not found:
                     raise ValueError("Could not find 'Strike' column")

            records_to_insert = []
            
            # Map column index to (contract, dte, type)
            col_map = {} # col_idx -> {'symbol': str, 'dte': int, 'type': 'C'|'P'}
            
            for col in range(df.shape[1]):
                if col == strike_col_idx:
                    continue
                
                header_val = str(df.iloc[0, col]).strip()
                sub_header_val = str(df.iloc[1, col]).strip()
                
                # Check for merged header logic: 
                # If header is "nan", it might belong to previous contract if pandas unmerged it?
                # Actually pandas reading with header=None reads raw cells. Merged cells usually put value in top-left, others nan.
                
                # Identify Contract
                # We need to track "last seen contract" for merged cells
                
                contract_header = header_val
                if contract_header == "nan":
                    # Check previous columns to find the contract this belongs to
                    # Assuming Structure: [Contract] [nan]
                    #                     [C]        [P]
                    # The contract header covers 2 columns.
                    # Go back to find non-nan
                    temp_col = col - 1
                    while temp_col >= 0:
                        val = str(df.iloc[0, temp_col]).strip()
                        if val != "nan":
                            contract_header = val
                            break
                        temp_col -= 1
                
                current_contract = None
                current_dte = 0
                
                if contract_header != "nan":
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

            # Now iterate rows for data
            for idx, row in df.iterrows():
                if idx < 2: continue # Skip headers
                
                strike_val = row[strike_col_idx]
                try:
                    strike = float(strike_val)
                    if pd.isna(strike): continue
                except:
                    continue
                
                # Temporary storage for this row's contract data
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
                    
                    key = (info['symbol'], strike)
                    if key not in row_data:
                        row_data[key] = {'dte': info['dte'], 'call': 0, 'put': 0}
                    
                    if info['type'] == 'C':
                        row_data[key]['call'] = val
                    elif info['type'] == 'P':
                        row_data[key]['put'] = val
                        
                for (symbol, strk), data in row_data.items():
                    records_to_insert.append({
                        'snapshot_at': snapshot_at,
                        'contract_symbol': symbol,
                        'dte': data['dte'],
                        'strike': strk,
                        'call_oi': data['call'],
                        'put_oi': data['put'],
                        'created_at': datetime.utcnow()
                    })

            if not records_to_insert:
                return {"status": "no_records_found"}

            stmt = insert(OpenInterest).values(records_to_insert)
            
            update_dict = {
                'call_oi': stmt.excluded.call_oi,
                'put_oi': stmt.excluded.put_oi,
                'dte': stmt.excluded.dte
            }
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['contract_symbol', 'strike', 'snapshot_at'],
                set_=update_dict
            )
            
            db.execute(stmt)
            db.commit()
            
            return {
                "status": "success", 
                "records_processed": len(records_to_insert),
                "snapshot_at": snapshot_at.isoformat()
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error parsing OI file: {e}")
            raise e
