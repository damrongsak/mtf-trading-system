import openpyxl
import io
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class COTParser:
    """
    Parses CFTC Disaggregated COT report (Excel/CSV).
    Focuses on 'GOLD - COMMODITY EXCHANGE INC.'
    """
    
    @staticmethod
    def parse(file_content: bytes, symbol: str = "GOLD") -> List[Dict[str, Any]]:
        """
        Parses Excel or CSV/TXT content and returns a list of COT records.
        Handles both Excel with headers and raw headerless CFTC text files.
        """
        try:
            # 1. Try parsing as Excel first
            df = pd.read_excel(io.BytesIO(file_content))
            has_headers = True
        except:
            # 2. Fallback to CSV/TXT
            # We try with and without headers
            sample = file_content[:1000].decode('utf-8', errors='ignore')
            if "Market_and_Exchange_Names" in sample:
                df = pd.read_csv(io.BytesIO(file_content))
                has_headers = True
            else:
                # Raw txt file usually doesn't have headers
                df = pd.read_csv(io.BytesIO(file_content), header=None)
                has_headers = False

        # Filter for Gold (usually 'GOLD - COMMODITY EXCHANGE INC.' in column 0)
        mask = df.iloc[:, 0].astype(str).str.contains(symbol, case=False, na=False)
        gold_df = df[mask]
        
        if gold_df.empty:
            logger.warning(f"No records found for symbol {symbol} in COT report.")
            return []

        records = []
        for _, row in gold_df.iterrows():
            try:
                # Map columns based on format
                if has_headers:
                    # Excel/CSV with headers
                    date_cols = [c for c in df.columns if 'date' in c.lower()]
                    report_date = pd.to_datetime(row[date_cols[0]]) if date_cols else datetime.utcnow()
                    
                    records.append({
                        'report_date': report_date,
                        'symbol': symbol,
                        'commercials_long': float(row.get('Comm_Positions_Long_All', row.get('Prod_Merc_Positions_Long_All', 0))),
                        'commercials_short': float(row.get('Comm_Positions_Short_All', row.get('Prod_Merc_Positions_Short_All', 0))),
                        'non_commercials_long': float(row.get('NonComm_Positions_Long_All', row.get('M_Money_Positions_Long_All', 0))),
                        'non_commercials_short': float(row.get('NonComm_Positions_Short_All', row.get('M_Money_Positions_Short_All', 0))),
                        'managed_money_long': float(row.get('M_Money_Positions_Long_All', 0)),
                        'managed_money_short': float(row.get('M_Money_Positions_Short_All', 0)),
                        'non_reportable_long': float(row.get('NonRept_Positions_Long_All', 0)),
                        'non_reportable_short': float(row.get('NonRept_Positions_Short_All', 0))
                    })
                else:
                    # Raw .txt file (Headerless index-based mapping)
                    # Indices based on Disaggregated Futures Only format
                    report_date = pd.to_datetime(row[2]) # Col 2 is YYYY-MM-DD
                    
                    records.append({
                        'report_date': report_date,
                        'symbol': symbol,
                        'commercials_long': float(row[8]),    # Prod_Merc_Positions_Long_All
                        'commercials_short': float(row[9]),   # Prod_Merc_Positions_Short_All
                        'non_commercials_long': float(row[13]), # M_Money_Positions_Long_All (Speculator proxy)
                        'non_commercials_short': float(row[14]),# M_Money_Positions_Short_All
                        'managed_money_long': float(row[13]),
                        'managed_money_short': float(row[14]),
                        'non_reportable_long': float(row[21]), # NonRept_Positions_Long_All
                        'non_reportable_short': float(row[22]) # NonRept_Positions_Short_All
                    })
            except Exception as e:
                logger.error(f"Error parsing COT row: {e}")
                continue
                
        return records
