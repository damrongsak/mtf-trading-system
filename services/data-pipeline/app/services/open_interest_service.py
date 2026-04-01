import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.repositories.open_interest_repository import OpenInterestRepository
from app.models.open_interest import OpenInterest
from app.schemas import (
    OpenInterestSnapshotResponse, 
    OpenInterestRecordResponse, 
    OpenInterestAnalysisResponse,
    AnalysisSummary,
    AnalysisDistribution
)
from app.utils.oi_parser import OpenInterestParser

logger = logging.getLogger(__name__)

class OpenInterestService:
    @staticmethod
    def parse_and_store(
        file_content: bytes, 
        db: Session, 
        snapshot_at: Optional[datetime] = None,
        underlying_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Parses Open Interest Matrix Excel and stores parsing results.
        """
        try:
            records_to_insert, snapshot_time = OpenInterestParser.parse(file_content, snapshot_at)
            
            if not records_to_insert:
                return {"status": "no_records_found"}

            # Bulk Insert / Upsert with Chunking to avoid Postgres parameter limits (65535)
            # 30k records * 9 columns = 270k parameters -> exceeds limit
            chunk_size = 500
            for i in range(0, len(records_to_insert), chunk_size):
                chunk = records_to_insert[i:i + chunk_size]
                
                stmt = insert(OpenInterest).values(chunk)
                
                update_dict = {
                    'call_oi': stmt.excluded.call_oi,
                    'put_oi': stmt.excluded.put_oi,
                    'dte': stmt.excluded.dte,
                    'underlying_price': stmt.excluded.underlying_price,
                    'underlying_contract_symbol': stmt.excluded.underlying_contract_symbol
                }
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=['contract_symbol', 'strike', 'snapshot_at'],
                    set_=update_dict
                )
                
                db.execute(stmt)
                
            db.commit()
            
            logger.info(f"Successfully processed {len(records_to_insert)} OI records for {snapshot_time}")
            return {
                "status": "success", 
                "records_processed": len(records_to_insert),
                "snapshot_at": snapshot_time.isoformat()
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
    def get_details(
        db: Session, 
        snapshot_at: datetime, 
        contract: Optional[str] = None, 
        min_oi: int = 0,
        max_oi: Optional[int] = None,
        smart_filter: bool = False,
        min_dte: Optional[int] = None,
        max_dte: Optional[int] = None
    ) -> List[OpenInterestRecordResponse]:
        """
        Get detailed Open Interest records for a specific snapshot.
        """
        repo = OpenInterestRepository(db)
        records = repo.get_by_snapshot(snapshot_at, contract, min_oi, max_oi, smart_filter, min_dte, max_dte)
        
        return [
            OpenInterestRecordResponse(
                contract_symbol=r.contract_symbol,
                dte=r.dte,
                strike=float(r.strike),
                call_oi=float(r.call_oi) if r.call_oi else 0.0,
                put_oi=float(r.put_oi) if r.put_oi else 0.0,
                underlying_price=float(r.underlying_price) if r.underlying_price else None,
                underlying_contract_symbol=r.underlying_contract_symbol
            ) 
            for r in records
        ]

    @staticmethod
    def get_analysis(
        db: Session, 
        snapshot_at: datetime, 
        contract_symbol: Optional[str] = None, 
        min_oi: int = 0,
        max_oi: Optional[int] = None,
        min_dte: Optional[int] = None,
        max_dte: Optional[int] = None
    ) -> OpenInterestAnalysisResponse:
        """
        Get aggregated analytics for a specific snapshot with optional filters.
        """
        repo = OpenInterestRepository(db)
        # Repository now handles aggregation and returns the final structure
        analysis_data = repo.get_analysis_data(snapshot_at, contract_symbol, min_oi, max_oi, smart_filter=True, min_dte=min_dte, max_dte=max_dte)
        
        return OpenInterestAnalysisResponse(
            summary=AnalysisSummary(**analysis_data['summary']),
            distribution=[AnalysisDistribution(**d) for d in analysis_data['distribution']]
        )

    @staticmethod
    def get_contracts(db: Session, snapshot_at: datetime) -> List[str]:
        """
        Get list of available contracts for a snapshot.
        """
        repo = OpenInterestRepository(db)
        return repo.get_available_contracts(snapshot_at)
