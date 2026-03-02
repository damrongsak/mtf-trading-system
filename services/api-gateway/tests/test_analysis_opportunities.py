"""
E2E Tests for GET /api/v1/analysis/opportunities

Tests the opportunity detection log endpoint which returns skipped trade
opportunities that were filtered out by Volatility/Sentiment filters.
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace
from sqlalchemy.exc import ProgrammingError, OperationalError

from app.models.opportunity_log import OpportunityLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_opportunity(**kwargs) -> SimpleNamespace:
    """
    Factory for a mock OpportunityLog-like object that Pydantic can serialize
    via from_attributes=True. Uses SimpleNamespace so attribute access works.
    """
    return SimpleNamespace(
        id=kwargs.get("id", uuid.uuid4()),
        timestamp=kwargs.get("timestamp", datetime(2026, 3, 1, 10, 0, 0)),
        symbol=kwargs.get("symbol", "XAUUSD"),
        timeframe=kwargs.get("timeframe", "H1"),
        direction=kwargs.get("direction", "BULLISH"),
        strategy_name=kwargs.get("strategy_name", "SMC_V2"),
        filter_name=kwargs.get("filter_name", "ATR_VOLATILITY"),
        filter_value=kwargs.get("filter_value", 0.5),
        threshold_value=kwargs.get("threshold_value", 1.0),
        reason=kwargs.get("reason", "ATR too low: 0.5 < 1.0"),
        meta_data=kwargs.get("meta_data", {"atr": 0.5, "ema200": 2300.0}),
    )


def _setup_db_query(mock_db_session, results: list):
    """Wire mock DB session so that query(OpportunityLog).order_by().limit().all() → results."""
    mock_query = MagicMock()
    mock_order_by = MagicMock()
    mock_limit = MagicMock()

    mock_db_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_order_by
    mock_order_by.limit.return_value = mock_limit
    mock_limit.all.return_value = results

    return mock_limit


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestGetOpportunitiesEmpty:
    """Empty table — should return an empty list, not an error."""

    def test_returns_empty_list(self, client, mock_db_session):
        _setup_db_query(mock_db_session, results=[])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert response.json() == []

    def test_default_limit_is_50(self, client, mock_db_session):
        _setup_db_query(mock_db_session, results=[])

        client.get("/api/v1/analysis/opportunities")

        mock_db_session.query.return_value.order_by.return_value.limit.assert_called_once_with(50)


class TestGetOpportunitiesPopulated:
    """Table has records — verify response structure and field values."""

    def test_returns_single_opportunity(self, client, mock_db_session):
        opp = _make_opportunity()
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_returns_multiple_opportunities(self, client, mock_db_session):
        opps = [
            _make_opportunity(symbol="XAUUSD", direction="BULLISH", filter_name="ATR_VOLATILITY"),
            _make_opportunity(symbol="XAUUSD", direction="BEARISH", filter_name="SENTIMENT"),
            _make_opportunity(symbol="EURUSD", direction="BULLISH", filter_name="VOLUME_PROFILE"),
        ]
        _setup_db_query(mock_db_session, results=opps)

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_opportunity_field_values(self, client, mock_db_session):
        opp_id = uuid.uuid4()
        opp = _make_opportunity(
            id=opp_id,
            symbol="XAUUSD",
            timeframe="H4",
            direction="BEARISH",
            strategy_name="SMC_V2",
            filter_name="SENTIMENT",
            filter_value=0.2,
            threshold_value=0.5,
            reason="Sentiment score too low: 0.2 < 0.5",
            meta_data={"sentiment_score": 0.2},
        )
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        record = response.json()[0]
        assert record["id"] == str(opp_id)
        assert record["symbol"] == "XAUUSD"
        assert record["timeframe"] == "H4"
        assert record["direction"] == "BEARISH"
        assert record["strategy_name"] == "SMC_V2"
        assert record["filter_name"] == "SENTIMENT"
        assert record["filter_value"] == pytest.approx(0.2)
        assert record["threshold_value"] == pytest.approx(0.5)
        assert record["reason"] == "Sentiment score too low: 0.2 < 0.5"
        assert record["meta_data"] == {"sentiment_score": 0.2}

    def test_meta_data_is_nullable(self, client, mock_db_session):
        opp = _make_opportunity(meta_data=None)
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert response.json()[0]["meta_data"] is None

    def test_strategy_name_is_nullable(self, client, mock_db_session):
        opp = _make_opportunity(strategy_name=None)
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert response.json()[0]["strategy_name"] is None


class TestGetOpportunitiesLimitParam:
    """Custom limit query parameter."""

    def test_custom_limit_applied(self, client, mock_db_session):
        _setup_db_query(mock_db_session, results=[])

        client.get("/api/v1/analysis/opportunities?limit=10")

        mock_db_session.query.return_value.order_by.return_value.limit.assert_called_once_with(10)

    def test_limit_1_only_returns_latest(self, client, mock_db_session):
        opp = _make_opportunity()
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities?limit=1")

        assert response.status_code == 200
        mock_db_session.query.return_value.order_by.return_value.limit.assert_called_once_with(1)

    def test_limit_100(self, client, mock_db_session):
        opps = [_make_opportunity() for _ in range(5)]
        _setup_db_query(mock_db_session, results=opps)

        response = client.get("/api/v1/analysis/opportunities?limit=100")

        assert response.status_code == 200
        mock_db_session.query.return_value.order_by.return_value.limit.assert_called_once_with(100)


class TestGetOpportunitiesFilterNames:
    """Verify all known filter types are handled correctly."""

    @pytest.mark.parametrize("filter_name", [
        "ATR_VOLATILITY",
        "SENTIMENT",
        "VOLUME_PROFILE",
        "REGIME_FILTER",
        "RRR_GUARD",
    ])
    def test_known_filter_names_return_200(self, client, mock_db_session, filter_name):
        opp = _make_opportunity(filter_name=filter_name)
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert response.json()[0]["filter_name"] == filter_name

    @pytest.mark.parametrize("direction", ["BULLISH", "BEARISH"])
    def test_trading_directions(self, client, mock_db_session, direction):
        opp = _make_opportunity(direction=direction)
        _setup_db_query(mock_db_session, results=[opp])

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 200
        assert response.json()[0]["direction"] == direction


class TestGetOpportunitiesDBError:
    """Database errors should return 500 with a meaningful message."""

    def test_undefined_table_raises_500(self, client, mock_db_session):
        mock_db_session.query.side_effect = ProgrammingError(
            "relation opportunity_logs does not exist",
            params={},
            orig=Exception("UndefinedTable"),
        )

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 500
        body = response.json()
        # App uses custom error envelope: {status, message, errors}
        assert body.get("status") == "error" or "detail" in body

    def test_db_connection_error_raises_500(self, client, mock_db_session):
        mock_db_session.query.side_effect = OperationalError(
            "could not connect to server",
            params={},
            orig=Exception("ConnectionRefused"),
        )

        response = client.get("/api/v1/analysis/opportunities")

        assert response.status_code == 500
        body = response.json()
        assert body.get("status") == "error" or "detail" in body
