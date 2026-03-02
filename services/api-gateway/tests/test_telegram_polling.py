"""
Unit tests for TelegramPollingService (Multi-Bot Manager)
=========================================================
Tests cover:
  1. manager_loop correctly starts/stops bot workers based on DB tokens.
  2. _bot_worker handles individual polling for a specific token.
  3. _process_update routes messages correctly for system vs personal bots.
  4. Decryption integration for personal bot tokens.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session_factory():
    """Minimal DB session factory that returns a mock session."""
    session = MagicMock()
    # Close should be a no-op or tracked
    session.close = MagicMock()
    
    factory = MagicMock(return_value=session)
    return factory, session


@pytest.fixture
def polling_service(mock_db_session_factory):
    from app.services.telegram_polling import TelegramPollingService
    factory, _ = mock_db_session_factory
    return TelegramPollingService(
        db_session_factory=factory,
        bot_token="SYSTEM_TOKEN",
        ai_analyst_url="http://ai-analyst:8000",
    )


# ---------------------------------------------------------------------------
# Test: Sync Bots Manager Logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_bots_starts_system_and_user_workers(polling_service, mock_db_session_factory):
    """_sync_bots should start workers for system token and any tokens in UserPreferences."""
    factory, session = mock_db_session_factory
    
    # 1. Mock DB data: one user with a personal bot
    user_id = uuid4()
    prefs = MagicMock()
    prefs.user_id = user_id
    prefs.telegram_bot_token = "ENCRYPTED_USER_TOKEN"
    
    session.query.return_value.filter.return_value.all.return_value = [prefs]
    
    # 2. Mock decryption
    with patch("app.services.telegram_polling.decrypt_token", return_value="DECRYPTED_USER_TOKEN") as mock_decrypt, \
         patch.object(polling_service, "_ensure_worker", new_callable=AsyncMock) as mock_ensure:
        
        await polling_service._sync_bots()
        
        # Should ensure system worker (user_id=None)
        # Should ensure user worker (user_id=user_id)
        assert mock_ensure.await_count == 2
        mock_ensure.assert_has_awaits([
            call(None, "SYSTEM_TOKEN"),
            call(user_id, "DECRYPTED_USER_TOKEN")
        ])

@pytest.mark.asyncio
async def test_sync_bots_stops_removed_workers(polling_service, mock_db_session_factory):
    """_sync_bots should stop workers if their tokens are removed from DB."""
    factory, session = mock_db_session_factory
    
    # Pre-populate workers
    user_id = uuid4()
    polling_service._user_tasks[user_id] = MagicMock()
    polling_service._user_tokens[user_id] = "OLD_TOKEN"
    
    # Mock DB: empty results (user removed token)
    session.query.return_value.filter.return_value.all.return_value = []
    
    with patch.object(polling_service, "_stop_worker", new_callable=AsyncMock) as mock_stop:
        await polling_service._sync_bots()
        mock_stop.assert_awaited_once_with(user_id)


# ---------------------------------------------------------------------------
# Test: Bot Worker Loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bot_worker_lifecycle(polling_service):
    """_bot_worker should delete webhook then poll updates."""
    token = "TEST_TOKEN"
    user_id = None
    
    with patch.object(polling_service, "_delete_webhook", new_callable=AsyncMock) as mock_del, \
         patch("httpx.AsyncClient") as mock_client_cls:
        
        # Stop polling after one iteration to avoid infinite loop in test
        polling_service._running = False 
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": []}
        
        async def mock_get(*args, **kwargs):
            await asyncio.sleep(0.1)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = mock_get
        mock_client_cls.return_value = mock_client
        
        # Run worker briefly
        polling_service._running = True
        # Use a short timeout to ensure the test returns
        try:
            await asyncio.wait_for(polling_service._bot_worker(user_id, token), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        finally:
            polling_service._running = False
        
        mock_del.assert_awaited_once_with(token)
        mock_client.get.assert_called()


# ---------------------------------------------------------------------------
# Test: Update Processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_update_personal_bot(polling_service, mock_db_session_factory):
    """Updates from a personal bot should automatically be attributed to the bot owner."""
    factory, session = mock_db_session_factory
    user_id = uuid4()
    update = {
        "message": {
            "chat": {"id": 12345},
            "message_id": 100,
            "text": "Hello bot",
        }
    }
    
    user = MagicMock()
    user.username = "personal_trader"
    user.id = user_id
    
    # Mock user lookup
    session.query.return_value.filter.return_value.first.return_value = user
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = MagicMock(status_code=200)
        mock_client_cls.return_value = mock_client
        
        await polling_service._process_update(update, "USER_TOKEN", user_id)
        
        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["user_id"] == "personal_trader"
        assert payload["telegram_chat_id"] == 12345


# ---------------------------------------------------------------------------
# Test: Graceful Stop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manager_stop_cancels_all_tasks(polling_service):
    """stop() should cancel the manager and all individual bot workers."""
    manager_task = AsyncMock()
    user_task = AsyncMock()
    
    polling_service._manager_task = manager_task
    polling_service._user_tasks[uuid4()] = user_task
    polling_service._running = True
    
    # Mock gather
    with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:
        await polling_service.stop()
        
        assert polling_service._running is False
        manager_task.cancel.assert_called_once()
        user_task.cancel.assert_called_once()
        mock_gather.assert_awaited_once()
