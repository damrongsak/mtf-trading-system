import openpyxl
import io
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# CFTC Disaggregated column mapping (works when file has headers)
CFTC_COL_MAP = {
    "commercials_long": ["Comm_Positions_Long_All", "Prod_Merc_Positions_Long_All"],
    "commercials_short": ["Comm_Positions_Short_All", "Prod_Merc_Positions_Short_All"],
    "non_commercials_long": ["NonComm_Positions_Long_All", "M_Money_Positions_Long_All"],
    "non_commercials_short": ["NonComm_Positions_Short_All", "M_Money_Positions_Short_All"],
    "managed_money_long": ["M_Money_Positions_Long_All"],
    "managed_money_short": ["M_Money_Positions_Short_All"],
    "non_reportable_long": ["NonRept_Positions_Long_All"],
    "non_reportable_short": ["NonRept_Positions_Short_All"],
}

# CFTC Disaggregated raw TXT column indices (0-indexed)
# Based on f_disagg.txt: Futures-only Disaggregated
# Mapping verified against 191-column Gold report row:
# Col 1: Symbol (idx 0)
# Col 3: Report Date YYYY-MM-DD (idx 2)
# Col 9: Prod_Merc_Long (idx 7)
# Col 10: Prod_Merc_Short (idx 8)
# Col 14: M_Money_Long (idx 13)
# Col 15: M_Money_Short (idx 14)
# Col 22: NonRept_Long (idx 21)
# Col 23: NonRept_Short (idx 22)
CFTC_RAW_IDX = {
    "report_date": 2,
    "prod_merc_long": 7,     # 0-indexed for 8th column
    "prod_merc_short": 8,    # 0-indexed for 9th column
    "m_money_long": 12,      # 0-indexed for 13th column
    "m_money_short": 13,     # 0-indexed for 14th column
    "non_rept_long": 20,     # 0-indexed for 21st column
    "non_rept_short": 21,    # 0-indexed for 22nd column
}


class COTParser:
    """
    Parses CFTC Disaggregated COT report (Excel/CSV/TXT).
    Focuses on 'GOLD - COMMODITY EXCHANGE INC.'
    """

    @staticmethod
    def _get_col_value(row, col_names: list, default=0.0) -> float:
        """Try multiple possible column names and return first found value."""
        for name in col_names:
            if name in row.index and pd.notnull(row[name]):
                try:
                    return float(row[name])
                except Exception:
                    pass
        return default

    @staticmethod
    def parse(file_content: bytes, symbol: str = "GOLD") -> List[Dict[str, Any]]:
        """
        Parses Excel or CSV/TXT content and returns a list of COT records.
        Handles both Excel with headers and raw headerless CFTC text files.
        """
        has_headers = False
        df = None

        # 1. Try parsing as Excel first
        try:
            df = pd.read_excel(io.BytesIO(file_content))
            has_headers = True
        except Exception:
            pass

        if df is None:
            # 2. CSV/TXT fallback
            sample = file_content[:2000].decode("utf-8", errors="ignore")
            has_headers = (
                "Market_and_Exchange_Names" in sample
                or "Market and Exchange Names" in sample
                or "Market" in sample.split("\n")[0]
            )
            try:
                if has_headers:
                    df = pd.read_csv(io.BytesIO(file_content))
                else:
                    df = pd.read_csv(io.BytesIO(file_content), header=None, low_memory=False)
            except Exception as e:
                logger.error(f"COT parse failed for all formats: {e}")
                return []

        if df is None or df.empty:
            return []

        # Filter for Symbol 
        # For Gold, we want to avoid "MICRO GOLD" if symbol is just "GOLD"
        if symbol.upper() == "GOLD":
            # Strict match for the primary Gold contract
            mask = df.iloc[:, 0].astype(str).str.contains("GOLD - COMMODITY EXCHANGE INC.", case=False, na=False)
        else:
            mask = df.iloc[:, 0].astype(str).str.contains(symbol, case=False, na=False)
            
        gold_df = df[mask]

        if gold_df.empty:
            logger.warning(f"No records found for symbol {symbol} in COT report.")
            # Fallback to broader search if strict fails
            mask = df.iloc[:, 0].astype(str).str.contains(symbol, case=False, na=False)
            gold_df = df[mask]

        records = []
        for _, row in gold_df.iterrows():
            try:
                if has_headers:
                    # Header-based column extraction (format-safe)
                    date_cols = [c for c in df.columns if "date" in str(c).lower()]
                    report_date = (
                        pd.to_datetime(row[date_cols[0]]) if date_cols else datetime.utcnow()
                    )

                    nc_long = COTParser._get_col_value(row, CFTC_COL_MAP["non_commercials_long"])
                    nc_short = COTParser._get_col_value(row, CFTC_COL_MAP["non_commercials_short"])
                    comm_long = COTParser._get_col_value(row, CFTC_COL_MAP["commercials_long"])
                    comm_short = COTParser._get_col_value(row, CFTC_COL_MAP["commercials_short"])
                    mm_long = COTParser._get_col_value(row, CFTC_COL_MAP["managed_money_long"])
                    mm_short = COTParser._get_col_value(row, CFTC_COL_MAP["managed_money_short"])
                    nr_long = COTParser._get_col_value(row, CFTC_COL_MAP["non_reportable_long"])
                    nr_short = COTParser._get_col_value(row, CFTC_COL_MAP["non_reportable_short"])

                else:
                    # Raw .txt file — index-based (CFTC f_disagg.txt layout)
                    idx = CFTC_RAW_IDX
                    max_col = max(idx.values())
                    if len(row) <= max_col:
                        logger.warning(f"COT raw row too short: {len(row)} cols. Skipping.")
                        continue

                    report_date = pd.to_datetime(row[idx["report_date"]])
                    nc_long = float(row[idx["m_money_long"]])
                    nc_short = float(row[idx["m_money_short"]])
                    comm_long = float(row[idx["prod_merc_long"]])
                    comm_short = float(row[idx["prod_merc_short"]])
                    mm_long = nc_long
                    mm_short = nc_short
                    nr_long = float(row[idx["non_rept_long"]])
                    nr_short = float(row[idx["non_rept_short"]])

                    if nc_long == 0 and nc_short == 0:
                        logger.warning(f"Parsed 0/0 non-commercial positions for {symbol} on {report_date}")

                records.append(
                    {
                        "report_date": report_date,
                        "symbol": symbol,
                        "commercials_long": comm_long,
                        "commercials_short": comm_short,
                        "non_commercials_long": nc_long,
                        "non_commercials_short": nc_short,
                        "managed_money_long": mm_long,
                        "managed_money_short": mm_short,
                        "non_reportable_long": nr_long,
                        "non_reportable_short": nr_short,
                    }
                )
                # If we found a valid non-zero record, we can stop for this symbol context
                if nc_long > 0 or nc_short > 0:
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing COT row: {e}")
                continue

        return records
