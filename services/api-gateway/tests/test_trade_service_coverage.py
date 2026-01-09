import pytest
from unittest.mock import MagicMock, call
from datetime import datetime
import uuid
from app.services.trade_service import TradeService
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.models.user import User
from app.models.journal import JournalEntry

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return user

def test_create_trade_from_execution_long(mock_db, mock_user):
    execution_data = {"id": "123", "price": "2000.0", "time": "2024-01-01T00:00:00"}
    request_data = {"symbol": "XAU/USD", "units": "100000", "sl_price": 1990.0, "tp_price": 2020.0}
    
    trade = TradeService.create_trade_from_execution(mock_db, mock_user, execution_data, request_data)
    
    # Check DB interactions
    assert mock_db.add.call_count == 2 # Trade + JournalEntry
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_with(trade)
    
    # Check Trade attributes
    assert trade.symbol == "XAU/USD"
    assert trade.direction == TradeDirection.LONG
    assert trade.entry_price == 2000.0
    assert trade.lot_size == 1.0 # 100000 units
    assert trade.metadata_json["oanda_id"] == "123"
    
    # Verify Journal Entry stub created
    args, _ = mock_db.add.call_args_list[1]
    journal_entry = args[0]
    assert isinstance(journal_entry, JournalEntry)
    assert journal_entry.user_id == mock_user.id
    assert journal_entry.symbol == "XAU/USD"
    assert journal_entry.direction == "LONG"

def test_create_trade_from_execution_short(mock_db, mock_user):
    execution_data = {"id": "124", "price": "1.1000", "time": "2024-01-01T00:00:00"}
    request_data = {"symbol": "EUR/USD", "units": "-50000", "sl_price": 1.1050, "tp_price": 1.0900}
    
    trade = TradeService.create_trade_from_execution(mock_db, mock_user, execution_data, request_data)
    
    assert trade.direction == TradeDirection.SHORT
    assert trade.lot_size == 0.5 # 50000 / 100000
    assert trade.entry_price == 1.1000

def test_close_trade_not_found(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = TradeService.close_trade(mock_db, "nonexistent", 2000.0)
    assert result is None

def test_close_trade_already_closed(mock_db):
    trade = MagicMock(spec=Trade)
    trade.status = TradeStatus.CLOSED
    mock_db.query.return_value.filter.return_value.first.return_value = trade
    
    result = TradeService.close_trade(mock_db, "closed_id", 2000.0)
    assert result == trade
    assert mock_db.commit.call_count == 0

def test_close_trade_long_profit_gold(mock_db):
    trade = Trade(
        trade_id=uuid.uuid4(),
        status=TradeStatus.OPEN, 
        direction=TradeDirection.LONG,
        entry_price=2000.00,
        lot_size=1.0, # $10 per pip
        symbol="XAU/USD"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = trade
    
    # Close at 2001.00 (+1 dollar move)
    # Gold pip is 0.01. Diff = 1.00 => 100 pips.
    # Value = 100 pips * ($10/pip * 1.0 lot) = $1000? 
    # Wait, code says:
    # diff = 1.00
    # pip_size = 0.01
    # pips = 100.0
    # val_per_pip = 1.0 * 10 = 10.0
    # pnl = 100 * 10 = 1000.0. Correct.
    
    result = TradeService.close_trade(mock_db, str(trade.trade_id), 2001.00)
    
    assert result.status == TradeStatus.CLOSED
    assert result.exit_price == 2001.00
    assert result.pnl_usd == 1000.0
    assert result.metadata_json["manual_close"] is True
    mock_db.commit.assert_called_once()

def test_close_trade_short_loss_euro(mock_db):
    trade = Trade(
        trade_id=uuid.uuid4(),
        status=TradeStatus.OPEN,
        direction=TradeDirection.SHORT,
        entry_price=1.1000,
        lot_size=0.1, # $1 per pip (standard)
        symbol="EUR/USD",
        metadata_json={}
    )
    mock_db.query.return_value.filter.return_value.first.return_value = trade
    
    # Close at 1.1010 (10 pips against)
    # Diff = (1.1010 - 1.1000) * -1 = 0.0010 * -1 = -0.0010
    # Pip = 0.0001
    # Pips = -10
    # Val = 0.1 * 10 = 1.0
    # PnL = -10 * 1.0 = -10.0
    
    result = TradeService.close_trade(mock_db, str(trade.trade_id), 1.1010)
    
    assert result.pnl_usd == pytest.approx(-10.0)
    assert result.status == TradeStatus.CLOSED

def test_sync_open_trades_existing(mock_db, mock_user):
    oanda_trades = [{"id": "100", "currentUnits": "100"}]
    
    existing_trade = MagicMock(spec=Trade)
    existing_trade.status = TradeStatus.OPEN
    existing_trade.metadata_json = {"oanda_id": "100"}
    existing_trade.broker_account_id = None
    
    mock_db.query.return_value.filter.return_value.first.return_value = existing_trade
    
    account_id = uuid.uuid4()
    results = TradeService.sync_open_trades(mock_db, oanda_trades, mock_user, account_id)
    
    assert len(results) == 1
    assert results[0] == existing_trade
    assert existing_trade.broker_account_id == account_id
    assert mock_db.add.call_count == 0 # No new trade added

def test_sync_open_trades_new(mock_db, mock_user):
    oanda_trades = [{
        "id": "101", 
        "currentUnits": "-100000", 
        "price": "2005.0", 
        "instrument": "XAU_USD",
        "openTime": "2024-01-01T10:00:00"
    }]
    
    # Mock query to return None (not found)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    results = TradeService.sync_open_trades(mock_db, oanda_trades, mock_user)
    
    assert len(results) == 1
    new_trade = results[0]
    assert new_trade.symbol == "XAU/USD"
    assert new_trade.entry_price == 2005.0
    assert new_trade.direction == TradeDirection.SHORT
    assert new_trade.metadata_json["oanda_id"] == "101"
    assert new_trade.strategy_name == "Oanda Sync"
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
