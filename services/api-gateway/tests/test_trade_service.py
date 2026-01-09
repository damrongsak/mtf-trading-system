import pytest
from unittest.mock import MagicMock, ANY
from datetime import datetime
import uuid
from app.services.trade_service import TradeService
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.models.journal import JournalEntry
from app.models.user import User

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = str(uuid.uuid4())
    return user

def test_create_trade_from_execution(mock_db_session, mock_user):
    execution_data = {
        "id": "oanda_123",
        "price": "2000.0",
        "time": "2023-01-01T12:00:00Z"
    }
    request_data = {
        "symbol": "XAU/USD",
        "units": 100000,
        "sl_price": 1990.0,
        "tp_price": 2010.0
    }
    
    trade = TradeService.create_trade_from_execution(mock_db_session, mock_user, execution_data, request_data)
    
    assert trade.symbol == "XAU/USD"
    assert trade.direction == TradeDirection.LONG
    assert trade.entry_price == 2000.0
    assert trade.lot_size == 1.0
    assert trade.metadata_json["oanda_id"] == "oanda_123"
    
    # Check Journal Entry creation
    mock_db_session.add.assert_called() # Called twice (Trade, JournalEntry)
    mock_db_session.commit.assert_called_once()


def test_close_trade_success(mock_db_session):
    trade_id = str(uuid.uuid4())
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_id = trade_id
    mock_trade.status = TradeStatus.OPEN
    mock_trade.entry_price = 2000.0
    mock_trade.direction = TradeDirection.LONG
    mock_trade.lot_size = 1.0
    mock_trade.symbol = "XAU/USD"
    mock_trade.metadata_json = {}
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_trade
    
    closed_trade = TradeService.close_trade(mock_db_session, trade_id, exit_price=2010.0)
    
    assert closed_trade.status == TradeStatus.CLOSED
    assert closed_trade.exit_price == 2010.0
    assert closed_trade.pnl_usd == 10000.0 # 1000 pips * $10/pip
    mock_db_session.commit.assert_called_once()

def test_close_trade_already_closed(mock_db_session):
    trade_id = str(uuid.uuid4())
    mock_trade = MagicMock(spec=Trade)
    mock_trade.status = TradeStatus.CLOSED
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_trade
    
    closed_trade = TradeService.close_trade(mock_db_session, trade_id, exit_price=2010.0)
    
    assert closed_trade == mock_trade
    mock_db_session.commit.assert_not_called()

def test_close_trade_not_found(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    result = TradeService.close_trade(mock_db_session, "missing_id", 2000.0)
    assert result is None

def test_sync_open_trades_new(mock_db_session, mock_user):
    oanda_trades = [{
        "id": "oanda_new_1",
        "currentUnits": "-100000",
        "price": "2000.0",
        "instrument": "XAU_USD",
        "openTime": "2023-01-01T12:00:00Z"
    }]
    
    # Mock no existing trade
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    synced = TradeService.sync_open_trades(mock_db_session, oanda_trades, mock_user)
    
    assert len(synced) == 1
    new_trade = synced[0]
    assert new_trade.metadata_json["oanda_id"] == "oanda_new_1"
    assert new_trade.direction == TradeDirection.SHORT
    assert new_trade.symbol == "XAU/USD"
    
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_sync_open_trades_existing(mock_db_session, mock_user):
    oanda_trades = [{
        "id": "oanda_exist_1"
    }]
    
    existing_trade = MagicMock(spec=Trade)
    existing_trade.trade_id = uuid.uuid4()
    existing_trade.broker_account_id = None
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_trade
    
    synced = TradeService.sync_open_trades(mock_db_session, oanda_trades, mock_user, broker_account_id=uuid.uuid4())
    
    assert len(synced) == 1
    # Check if broker link updated
    assert existing_trade.broker_account_id is not None
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()
