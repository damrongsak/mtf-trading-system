import logging
import traceback
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.cot import COTRecord
from app.utils.cot_parser import COTParser

logger = logging.getLogger(__name__)

class COTService:
    @staticmethod
    def parse_and_store(file_content: bytes, db: Session, symbol: str = "GOLD") -> Dict[str, Any]:
        """
        Parses COT report and stores it in the database using UPSERT.
        """
        try:
            records = COTParser.parse(file_content, symbol)
            if not records:
                return {"status": "warning", "message": f"No records found for {symbol}"}

            stored_count = 0
            for rec in records:
                stmt = insert(COTRecord).values(
                    id=uuid.uuid4(),
                    report_date=rec['report_date'],
                    symbol=rec['symbol'],
                    commercials_long=rec['commercials_long'],
                    commercials_short=rec['commercials_short'],
                    non_commercials_long=rec['non_commercials_long'],
                    non_commercials_short=rec['non_commercials_short'],
                    managed_money_long=rec['managed_money_long'],
                    managed_money_short=rec['managed_money_short'],
                    non_reportable_long=rec['non_reportable_long'],
                    non_reportable_short=rec['non_reportable_short'],
                    created_at=datetime.utcnow()
                )

                # Upsert logic
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_cot_records_symbol_report_date',
                    set_={
                        'commercials_long': stmt.excluded.commercials_long,
                        'commercials_short': stmt.excluded.commercials_short,
                        'non_commercials_long': stmt.excluded.non_commercials_long,
                        'non_commercials_short': stmt.excluded.non_commercials_short,
                        'managed_money_long': stmt.excluded.managed_money_long,
                        'managed_money_short': stmt.excluded.managed_money_short,
                        'non_reportable_long': stmt.excluded.non_reportable_long,
                        'non_reportable_short': stmt.excluded.non_reportable_short,
                    }
                )
                db.execute(stmt)
                stored_count += 1
            
            db.commit()
            return {
                "status": "success", 
                "message": f"Successfully processed {stored_count} COT records for {symbol}",
                "records_count": stored_count
            }

        except Exception as e:
            db.rollback()
            logger.error(f"COT Ingestion failed: {e}")
            logger.error(traceback.format_exc())
            raise e

    @staticmethod
    def get_latest_sentiment(db: Session, symbol: str = "GOLD") -> Dict[str, Any]:
        """
        Returns the latest COT sentiment summary.
        """
        latest = db.query(COTRecord).filter(
            COTRecord.symbol == symbol
        ).order_by(COTRecord.report_date.desc()).first()

        if not latest:
            return None

        # Logic for Net Positioning and Bias
        # Non-Commercials (Speculators) are often used for trend bias
        net_non_comm = float(latest.non_commercials_long - latest.non_commercials_short)
        
        return {
            "report_date": latest.report_date,
            "symbol": latest.symbol,
            "net_non_commercial": net_non_comm,
            "non_commercials_long": float(latest.non_commercials_long),
            "non_commercials_short": float(latest.non_commercials_short),
            "commercials_long": float(latest.commercials_long),
            "commercials_short": float(latest.commercials_short),
            "managed_money_net": float((latest.managed_money_long or 0) - (latest.managed_money_short or 0))
        }

cot_service = COTService()
