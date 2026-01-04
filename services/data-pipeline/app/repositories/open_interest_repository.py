from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from typing import List, Optional
from app.models.open_interest import OpenInterest
import logging

logger = logging.getLogger(__name__)

class OpenInterestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_snapshots(self, limit: int = 20):
        """
        Get list of available Open Interest snapshots.
        """
        return self.db.query(
            OpenInterest.snapshot_at,
            func.count(OpenInterest.id).label('count'),
            func.max(OpenInterest.created_at).label('created_at')
        ).group_by(OpenInterest.snapshot_at)\
         .order_by(desc(OpenInterest.snapshot_at))\
         .limit(limit)\
         .all()

    def get_by_snapshot(self, snapshot_at: datetime) -> List[OpenInterest]:
        """
        Get all Open Interest records for a specific snapshot.
        """
        return self.db.query(OpenInterest).filter(
            OpenInterest.snapshot_at == snapshot_at
        ).order_by(OpenInterest.strike).all()
        
    def get_analysis_data(self, snapshot_at: datetime) -> List[OpenInterest]:
        """
        Get unsorted records for analysis (faster than sorted).
        """
        return self.db.query(OpenInterest).filter(
            OpenInterest.snapshot_at == snapshot_at
        ).all()
