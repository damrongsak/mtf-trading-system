import pandas as pd
import io
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.repositories.open_interest_repository import OpenInterestRepository
from app.schemas import (
    OpenInterestSnapshotResponse, 
    OpenInterestRecordResponse, 
    OpenInterestAnalysisResponse,
    AnalysisSummary,
    AnalysisDistribution
)
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
            
            # Find Header Row & Strike Column
            header_row_idx = -1
            strike_col_idx = -1
            
            # Optimization: Read first 20 rows to find header
            preview_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=20)
            
            for r in range(preview_df.shape[0]):
                for c in range(preview_df.shape[1]):
                    val = str(preview_df.iloc[r, c]).strip()
                    if val.lower() == "strike":
                        header_row_idx = r
                        strike_col_idx = c
                        break
                if header_row_idx != -1:
                    break
            
            if header_row_idx == -1:
                raise ValueError("Could not find 'Strike' column in first 20 rows.")

            # Re-read dataframe starting from header row
            # We explicitly read without header again to handle multi-line headers manually via iloc, 
            # but we skiprows up to the header row.
            # Actually, to access row+1 (C/P), we need to read from header_row_idx.
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=header_row_idx)
            # Now row 0 is header (Strike, Contract...), row 1 is subheader (C/P)
            
            # Reset strike_col_idx relative to new df (it should technically be the same col index if we didn't drop columns, 
            # but skiprows doesn't drop columns, usually. However, read_excel might behave differently if empty cols exist)
            # Let's re-verify strike in row 0 of new df
            strike_col_idx = -1
            for c in range(df.shape[1]):
                if str(df.iloc[0,c]).strip().lower() == "strike":
                    strike_col_idx = c
                    break
            
            if strike_col_idx == -1:
                 raise ValueError("Could not verify 'Strike' column after adjustment.")

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

    @staticmethod
    def get_snapshots(db: Session, limit: int = 20) -> List[OpenInterestSnapshotResponse]:
        """
        Get list of available Open Interest snapshots.
        """
        repo = OpenInterestRepository(db)
        results = repo.get_snapshots(limit)
        
        return [
            OpenInterestSnapshotResponse(
                snapshot_at=r.snapshot_at,
                count=r.count,
                created_at=r.created_at
            )
            for r in results
        ]

    @staticmethod
    def get_details(db: Session, snapshot_at: datetime) -> List[OpenInterestRecordResponse]:
        """
        Get detailed Open Interest records for a specific snapshot.
        """
        repo = OpenInterestRepository(db)
        records = repo.get_by_snapshot(snapshot_at)
        
        return [
            OpenInterestRecordResponse(
                contract_symbol=r.contract_symbol,
                dte=r.dte,
                strike=float(r.strike),
                call_oi=float(r.call_oi) if r.call_oi else 0.0,
                put_oi=float(r.put_oi) if r.put_oi else 0.0
            ) 
            for r in records
        ]

    @staticmethod
    def get_analysis(db: Session, snapshot_at: datetime) -> OpenInterestAnalysisResponse:
        """
        Get aggregated analytics for a specific snapshot.
        """
        repo = OpenInterestRepository(db)
        records = repo.get_analysis_data(snapshot_at)
        
        if not records:
             # Return empty structure if no data
            return OpenInterestAnalysisResponse(
                summary=AnalysisSummary(
                    total_call_oi=0, total_put_oi=0, pcr=0, max_call_strike=0, max_put_strike=0
                ),
                distribution=[]
            )
            
        total_call_oi = 0
        total_put_oi = 0
        max_call_oi = 0
        max_call_strike = 0
        max_put_oi = 0
        max_put_strike = 0
        
        distribution_by_strike = {}
        
        for r in records:
            c_oi = float(r.call_oi) if r.call_oi else 0
            p_oi = float(r.put_oi) if r.put_oi else 0
            strike = float(r.strike)
            
            total_call_oi += c_oi
            total_put_oi += p_oi
            
            if c_oi > max_call_oi:
                max_call_oi = c_oi
                max_call_strike = strike
                
            if p_oi > max_put_oi:
                max_put_oi = p_oi
                max_put_strike = strike
                
            if strike not in distribution_by_strike:
                distribution_by_strike[strike] = {'call_oi': 0.0, 'put_oi': 0.0}
            
            distribution_by_strike[strike]['call_oi'] += c_oi
            distribution_by_strike[strike]['put_oi'] += p_oi
            
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Format distribution for charts (list of objects)
        chart_data = []
        for strike in sorted(distribution_by_strike.keys()):
            chart_data.append(AnalysisDistribution(
                strike=strike,
                call_oi=distribution_by_strike[strike]['call_oi'],
                put_oi=distribution_by_strike[strike]['put_oi'],
                net_delta=distribution_by_strike[strike]['call_oi'] - distribution_by_strike[strike]['put_oi']
            ))
            
        return OpenInterestAnalysisResponse(
            summary=AnalysisSummary(
                total_call_oi=total_call_oi,
                total_put_oi=total_put_oi,
                pcr=round(pcr, 4),
                max_call_strike=max_call_strike,
                max_put_strike=max_put_strike
            ),
            distribution=chart_data
        )
