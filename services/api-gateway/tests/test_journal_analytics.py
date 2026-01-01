from unittest.mock import MagicMock
from app.models.journal import JournalEntry, TimelineEvent, RootCauseAnalysis, GameLevel
from app.schemas.response import ResponseStatus
import uuid
from datetime import datetime, timedelta, timezone

def test_get_journal_stats(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # Mock base query for count
    # base_query = db.query(JournalEntry).filter(...)
    mock_base_query = mock_db_session.query.return_value.filter.return_value
    mock_base_query.count.return_value = 10
    
    # Mock aggregations
    # Because there are multiple queries, we need to inspect the query structure or use side_effect
    # But simpler is to assume sequential calls or specific mock targets if possible.
    # However, SQLAlchemy mocking is tricky for multiple different queries on same session.mock.
    
    # Strategy: Side effect on the chain
    # 1. Total trades: query(JournalEntry).filter().count() -> 10
    # 2. Net PnL: query(sum).filter.scalar() -> 500
    # 3. Wins: filter(pnl>0).count() -> 6
    # 4. Losses: filter(pnl<=0).count() -> 4
    # 5. Gross Profit: query(sum).filter(>0).scalar() -> 1000
    # 6. Gross Loss: query(sum).filter(<0).scalar() -> -500
    # 7. Series: query(pnl).order_by.all() -> [-50, 100, ...]
    
    # Mocking `db.query(...)`
    # We can distinguish by arguments to `query()`.
    def query_side_effect(*args):
        mock_q = MagicMock()
        
        # Check if querying JournalEntry model directly (for count)
        if args and args[0] == JournalEntry:
            # For wins calculation: filter is called with expression.
            # We can just return a generic mock that returns specific counts based on call order?
            # Or simplified: just mock distinct chains if possible.
            # Given the complexity, let's mock the final values directly if possible? No, logic is in router.
            pass
            
        return mock_q

    # Let's try setting up specific return values for the sequence of calls we expect.
    # This is brittle but standard for deep mocking.
    
    # 1. db.query(JournalEntry).filter(...).count()
    # 2. db.query(func.sum).filter(...).scalar()
    # 3. db.query(JournalEntry).filter(...).filter(pnl>0).count()
    # ...
    
    # This is too complex to mock strictly with standard MagicMock chaining for all cases.
    # We will try a simpler approach: Mock the "happy path" where everything returns *something*.
    
    msg = mock_db_session.query.return_value
    # Make filter return self to handle chaining
    msg.filter.return_value = msg
    msg.order_by.return_value = msg
    
    # Net PnL scalar
    msg.filter.return_value.scalar.return_value = 500.0
    
    # filter().count() - returns 10 initially, then 6 (wins), then 4 (losses)
    msg.filter.return_value.count.side_effect = [10, 6, 4] 
    # Wait, the code calls `base_query.count()`. base_query is `query(JournalEntry).filter`.
    # Then `base_query.filter(>0).count()`.
    # So `count` is called on the result of `filter`.
    # The chain is `query -> filter -> count` and `query -> filter -> filter -> count`.
    
    # Let's simplify and just ensure 200 OK and structure.
    # mocking scalar returns for calculations
    msg.filter.return_value.scalar.side_effect = [500.0, 1000.0, -500.0]
    
    # Mock Scalar results for PnL
    # The logic calls:
    # 1. net_pnl = scalar()
    # 2. gross_profit = scalar()
    # 3. gross_loss = scalar()
    # 4. pnl_series = all() -> flattened
    
    # We can use side_effect on scalar() to return the 3 values in order
    msg.filter.return_value.scalar.side_effect = [500.0, 1000.0, -500.0]
    
    # Mock Series
    # The code calls: query(pnl).filter.order_by.all()
    # We need to ensure the chain allows for this.
    # msg is query.return_value
    # msg.filter.return_value is what we attach scalar to.
    # The code does `db.query(JournalEntry.pnl_amount)` which is a different query object than `db.query(JournalEntry)`.
    # MagicMock usually treats them same unless we differentiate.
    # Let's attach the .all() return value to the same chain.
    msg.filter.return_value.order_by.return_value.all.return_value = [(100.0,), (-50.0,), (200.0,)]

    response = client.get("/api/v1/journal/analytics/stats")
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["net_pnl"] == 500.0
    # win_rate: count() returned 10 initially. 
    # winning_trades count call: base_query.filter().count()
    # losing_trades count call: base_query.filter().count()
    # We set count side effect to [10, 6, 4].
    # So total=10, win=6, loss=4. Win rate = 60%.
    assert data["win_rate"] == 60.0
    assert data["avg_win"] == 1000.0 / 6
    
    app.dependency_overrides.pop(get_current_user)

def test_get_equity_curve(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # Mock return entries
    mock_entry1 = MagicMock()
    mock_entry1.created_at = datetime.now(timezone.utc)
    mock_entry1.pnl_amount = 100.0
    
    mock_entry2 = MagicMock()
    mock_entry2.created_at = datetime.now(timezone.utc)
    mock_entry2.pnl_amount = 50.0
    
    # The router calls: db.query(...).filter(...).order_by(...).all()
    # So we attach return value to the end of that chain.
    msg = mock_db_session.query.return_value
    msg.filter.return_value = msg
    msg.order_by.return_value = msg
    msg.all.return_value = [mock_entry1, mock_entry2]
    
    response = client.get("/api/v1/journal/analytics/equity")
    
    assert response.status_code == 200
    data = response.json()["data"]
    # Expect 3 points because code adds a placeholder (0,0) at start.
    assert len(data) == 3
    assert data[1]["balance"] == 100.0
    assert data[2]["balance"] == 150.0
    
    app.dependency_overrides.pop(get_current_user)

def test_get_pattern_analysis(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # This endpoint does 3 queries.
    # 1. Game Levels: query(GameLevel, count, avg).filter.group.all
    # 2. Emotions: query(Desc, count).join.filter.group.order.limit.all
    # 3. Mistakes: query(Flaw, count).join.filter.group.order.limit.all
    
    # We can mock side_effect for the 'all' call
    
    # Mock Result Tuples
    gl_result = [("A_GAME", 5, 200.0)]
    emotion_result = [("Fear", 3)]
    mistake_result = [("FOMO", 2)]
    
    # Setup chain
    msg = mock_db_session.query.return_value
    msg.filter.return_value = msg
    msg.group_by.return_value = msg
    msg.order_by.return_value = msg
    msg.limit.return_value = msg
    msg.join.return_value = msg
    
    # .all() side effect for the 3 queries
    msg.all.side_effect = [gl_result, emotion_result, mistake_result]
    
    response = client.get("/api/v1/journal/analytics/patterns")
    
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["game_levels"][0]["name"] == "A_GAME"
    assert data["top_emotions"][0]["name"] == "Fear"
    assert data["top_mistakes"][0]["name"] == "FOMO"
    
    app.dependency_overrides.pop(get_current_user)
