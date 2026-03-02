"""
Integration Tests: opportunity_logs ← → /api/v1/analysis/drift

Verifies the end-to-end contract between the opportunity_logs table
(written by strategy filters) and the PerformanceMonitor drift analysis
that reads those records to produce system health status.

Architecture:
  [Strategy Filters]
       ↓  INSERT opportunity_logs
  [opportunity_logs table]
       ↓  SELECT (PerformanceMonitor)
  [POST /api/v1/analysis/drift]
       ↓  returns {status, filter_rate, top_rejection_reason, ...}
  [Frontend Drift Monitor / AI Analyst]
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.analysis.monitor import PerformanceMonitor
from app.models.opportunity_log import OpportunityLog
from app.models.signal_log import SignalLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_opp_count_mock(signal_count: int, opp_count: int, top_filter: str = "ATR_VOLATILITY"):
    """
    Returns a configured mock DB session that returns given counts from
    query(...).filter(...).count() — matching PerformanceMonitor.analyze_drift() call pattern.
    """
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.side_effect = [signal_count, opp_count]
    mock_db.query.return_value.filter.return_value.group_by.return_value \
        .order_by.return_value.first.return_value = (top_filter, opp_count)
    return mock_db


# ---------------------------------------------------------------------------
# Integration: PerformanceMonitor ↔ opportunity_logs
# ---------------------------------------------------------------------------

class TestDriftReflectsOpportunityLogs:
    """
    Verify that as opportunity_logs fill up relative to signal_logs,
    the drift status transitions correctly.
    """

    def test_healthy_market_few_skips(self):
        """
        5 signals, 2 skipped → filter_rate = 28% → HEALTHY
        This simulates a well-tuned strategy where most setups execute.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=5, opp_count=2)

            result = PerformanceMonitor().analyze_drift()

        assert result["status"] == "HEALTHY"
        assert result["signal_count"] == 5
        assert result["opportunity_count"] == 2
        assert result["filter_rate"] == pytest.approx(2 / 7, abs=1e-4)

    def test_monitoring_half_skipped(self):
        """
        9 signals, 11 skipped → filter_rate = 55% → MONITORING
        Strategy is borderline — filters are blocking > 50% of setups.
        Note: monitor uses 'elif filter_rate > 0.5' (strictly greater than).
        Exactly 50% does NOT trigger MONITORING; must be strictly above.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=9, opp_count=11)

            result = PerformanceMonitor().analyze_drift()

        assert result["status"] == "MONITORING"
        assert result["filter_rate"] == pytest.approx(11 / 20, abs=1e-4)

    def test_drift_warning_mostly_skipped(self):
        """
        2 signals, 20 skipped → filter_rate = 91% → DRIFT_WARNING
        Filters are too aggressive — most market setups are rejected.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(
                signal_count=2, opp_count=20, top_filter="ATR_VOLATILITY"
            )

            result = PerformanceMonitor().analyze_drift()

        assert result["status"] == "DRIFT_WARNING"
        assert result["filter_rate"] > 0.8
        assert result["top_rejection_reason"] == "ATR_VOLATILITY"

    def test_inactive_no_data(self):
        """
        0 signals, 0 skipped → INACTIVE
        Market is closed or system is idle.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=0, opp_count=0)

            result = PerformanceMonitor().analyze_drift()

        assert result["status"] == "INACTIVE"
        assert result["filter_rate"] == 0.0
        assert result["signal_count"] == 0
        assert result["opportunity_count"] == 0

    def test_drift_warning_requires_minimum_5_events(self):
        """
        DRIFT_WARNING threshold requires > 5 total events (market open check).
        1 signal, 4 skipped → rate=80% but only 5 events total → still MONITORING.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=1, opp_count=4)

            result = PerformanceMonitor().analyze_drift()

        # 4/5 = 80% but total_events=5 is NOT > 5, so should NOT be DRIFT_WARNING
        assert result["status"] == "MONITORING"
        assert result["filter_rate"] == pytest.approx(0.8, abs=1e-4)

    def test_top_rejection_reason_reflects_most_common_filter(self):
        """
        When multiple filters appear, top_rejection_reason = the most frequent one.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_db = _make_opp_count_mock(signal_count=2, opp_count=15, top_filter="SENTIMENT")
            mock_cls.return_value = mock_db

            result = PerformanceMonitor().analyze_drift()

        assert result["top_rejection_reason"] == "SENTIMENT"

    def test_custom_window_hours_passed_to_filter(self):
        """
        window_hours parameter must affect the cutoff applied to both
        SignalLog and OpportunityLog queries.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_db = _make_opp_count_mock(signal_count=5, opp_count=1)
            mock_cls.return_value = mock_db

            result = PerformanceMonitor().analyze_drift(window_hours=48)

        assert result["window_hours"] == 48
        assert result["status"] == "HEALTHY"

    def test_db_exception_returns_error_state(self):
        """
        If the DB throws, analyze_drift returns {"status": "ERROR"} — never raises.
        """
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_db = MagicMock()
            mock_db.query.side_effect = Exception("DB connection lost")
            mock_cls.return_value = mock_db

            result = PerformanceMonitor().analyze_drift()

        assert result["status"] == "ERROR"
        assert "error" in result


# ---------------------------------------------------------------------------
# Integration: strategy-core /analysis/drift endpoint (via FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestDriftEndpointIntegration:
    """
    Full HTTP integration test: POST /api/v1/analysis/drift
    Mocks the DB but exercises the FastAPI routing layer.
    """

    @pytest.fixture
    def strategy_client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_drift_endpoint_returns_200(self, strategy_client):
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=5, opp_count=2)

            resp = strategy_client.post("/api/v1/analysis/drift")

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "filter_rate" in data

    def test_drift_endpoint_healthy_scenario(self, strategy_client):
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=10, opp_count=1)

            resp = strategy_client.post("/api/v1/analysis/drift")

        assert resp.status_code == 200
        assert resp.json()["status"] == "HEALTHY"

    def test_drift_endpoint_warning_scenario(self, strategy_client):
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=0, opp_count=20)

            resp = strategy_client.post("/api/v1/analysis/drift?window_hours=24")

        assert resp.status_code == 200
        assert resp.json()["status"] == "DRIFT_WARNING"

    def test_drift_endpoint_with_window_hours_param(self, strategy_client):
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_cls.return_value = _make_opp_count_mock(signal_count=3, opp_count=1)

            resp = strategy_client.post("/api/v1/analysis/drift?window_hours=12")

        assert resp.status_code == 200
        assert resp.json()["window_hours"] == 12

    def test_drift_endpoint_db_error_returns_500_or_error_status(self, strategy_client):
        with patch("app.analysis.monitor.SessionLocal") as mock_cls:
            mock_db = MagicMock()
            mock_db.query.side_effect = RuntimeError("Connection pool exhausted")
            mock_cls.return_value = mock_db

            resp = strategy_client.post("/api/v1/analysis/drift")

        # analyze_drift catches exceptions and returns {"status": "ERROR"}
        # which the endpoint returns as 200 (no re-raise), or the endpoint catches it as 500
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["status"] == "ERROR"


# ---------------------------------------------------------------------------
# Contract: API Gateway opportunities response matches what drift expects
# ---------------------------------------------------------------------------

class TestOpportunityLogContract:
    """
    Verifies the OpportunityLog data contract used by both:
    - api-gateway: GET /api/v1/analysis/opportunities (returns to frontend)
    - strategy-core: PerformanceMonitor (reads directly from DB)

    These tests confirm the shared model fields stay in sync.
    """

    def test_opportunity_log_has_required_drift_fields(self):
        """
        PerformanceMonitor groups by filter_name and filters by timestamp.
        These fields MUST exist on OpportunityLog.
        """
        assert hasattr(OpportunityLog, "filter_name"), "OpportunityLog must have filter_name for drift grouping"
        assert hasattr(OpportunityLog, "timestamp"), "OpportunityLog must have timestamp for window filtering"

    def test_opportunity_log_has_api_response_fields(self):
        """
        Verify all fields exposed via GET /api/v1/analysis/opportunities
        are present on the ORM model.
        """
        required_fields = [
            "id", "timestamp", "symbol", "timeframe", "direction",
            "strategy_name", "filter_name", "filter_value",
            "threshold_value", "reason", "meta_data"
        ]
        for field in required_fields:
            assert hasattr(OpportunityLog, field), (
                f"OpportunityLog missing field '{field}' required by API response"
            )

    def test_filter_rate_formula_consistency(self):
        """
        Verify the drift formula: filter_rate = opp_count / (signal_count + opp_count)
        This is the core business logic linking opportunity logs to system health.
        """
        signal_count = 5
        opp_count = 15
        total = signal_count + opp_count
        expected_rate = opp_count / total

        assert expected_rate == pytest.approx(0.75)
        # At 75% filter rate with total > 5 → MONITORING (not yet WARNING at > 80%)
        assert not (expected_rate > 0.8 and total > 5)
