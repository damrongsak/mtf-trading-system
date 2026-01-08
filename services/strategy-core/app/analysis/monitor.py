from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.signal_log import SignalLog
from app.models.opportunity_log import OpportunityLog
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        pass

    def analyze_drift(self, window_hours: int = 24):
        """
        Analyze system drift by checking the ratio of executed trades vs skipped opportunities.
        High skip rate suggests unmatched market conditions (Strategy Drift).
        """
        db: Session = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=window_hours)
            
            # 1. Count Executed Signals
            signal_count = db.query(SignalLog).filter(SignalLog.timestamp >= cutoff).count()
            
            # 2. Count Skipped Opportunities (Filters triggered)
            opp_count = db.query(OpportunityLog).filter(OpportunityLog.timestamp >= cutoff).count()
            
            total_events = signal_count + opp_count
            
            if total_events == 0:
                return {
                    "status": "INACTIVE",
                    "filter_rate": 0.0,
                    "signal_count": 0,
                    "opportunity_count": 0,
                    "reason": "No data in window"
                }
                
            filter_rate = opp_count / total_events
            
            # 3. Identify Top Reject Reason
            top_reason = "None"
            if opp_count > 0:
                # Group by filter_name
                from sqlalchemy import func
                most_frequent = db.query(
                    OpportunityLog.filter_name, 
                    func.count(OpportunityLog.filter_name)
                ).filter(
                    OpportunityLog.timestamp >= cutoff
                ).group_by(
                    OpportunityLog.filter_name
                ).order_by(
                    func.count(OpportunityLog.filter_name).desc()
                ).first()
                
                if most_frequent:
                    top_reason = most_frequent[0]

            # 4. Status Determination
            status = "HEALTHY"
            if filter_rate > 0.8 and total_events > 5:
                status = "DRIFT_WARNING"
            elif filter_rate > 0.5:
                status = "MONITORING"
                
            return {
                "status": status,
                "filter_rate": round(filter_rate, 4),
                "signal_count": signal_count,
                "opportunity_count": opp_count,
                "top_rejection_reason": top_reason,
                "window_hours": window_hours
            }
            
        except Exception as e:
            logger.error(f"Drift analysis failed: {e}")
            return {"status": "ERROR", "error": str(e)}
        finally:
            db.close()

performance_monitor = PerformanceMonitor()
