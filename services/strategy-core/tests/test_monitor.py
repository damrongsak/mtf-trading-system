import pytest
from unittest.mock import MagicMock, patch
from app.analysis.monitor import PerformanceMonitor

def test_analyze_drift_healthy():
    # Scenario: 5 Signals, 2 Opportunities (Skipped)
    # Total = 7. Skips = 2. Rate = 0.28. Status = HEALTHY.
    
    with patch("app.analysis.monitor.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        # Mock Counts
        # signal query -> filter -> count
        mock_db.query.return_value.filter.return_value.count.side_effect = [5, 2]
        
        # Mock Top Reason (Not needed for healthy but code asks)
        mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.first.return_value = ("ATR", 2)
        
        monitor = PerformanceMonitor()
        result = monitor.analyze_drift()
        
        assert result['status'] == "HEALTHY"
        assert result['filter_rate'] == pytest.approx(0.2857, 0.0001)

def test_analyze_drift_warning():
    # Scenario: 0 Signals, 20 Opportunities (Skipped)
    # Total = 20. Skips = 20. Rate = 1.0. Status = DRIFT_WARNING.
    
    with patch("app.analysis.monitor.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        # Mock Counts: 0 signals, 20 skips
        mock_db.query.return_value.filter.return_value.count.side_effect = [0, 20]
        
        # Mock Top Reason
        mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.first.return_value = ("ATR_VOLATILITY", 15)
        
        monitor = PerformanceMonitor()
        result = monitor.analyze_drift()
        
        assert result['status'] == "DRIFT_WARNING"
        assert result['filter_rate'] == 1.0
        assert result['top_rejection_reason'] == "ATR_VOLATILITY"

def test_analyze_drift_inactive():
    # Scenario: 0 events
    with patch("app.analysis.monitor.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.count.side_effect = [0, 0]
        
        monitor = PerformanceMonitor()
        result = monitor.analyze_drift()
        
        assert result['status'] == "INACTIVE"
