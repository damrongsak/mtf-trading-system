from typing import Dict, Any
from app.adapters.ctrader_client import AsyncCTraderClient
import logging

def _global_ctrader_handler(msg):
    """
    [HFT-lite] Global message handler for all cTrader connections.
    Routes unsolicited events (fills, spots) to the appropriate processors.
    """
    logger.debug(f"Global cTrader Handler: Received message type {msg.payloadType}")
    try:
        from app.adapters.ctrader import CTraderMessageRouter
        CTraderMessageRouter.handle_unsolicited_message(msg)
    except Exception as e:
        # Avoid circular import or missing router issues during startup
        logging.getLogger(__name__).error(f"Global cTrader handler error: {e}")

logger = logging.getLogger(__name__)

class CTraderConnectionManager:
    _clients: Dict[str, AsyncCTraderClient] = {}

    @classmethod
    def get_client(cls, host: str, port: int, account_id: str) -> AsyncCTraderClient:
        """
        Get an existing client for the account or create a new one.
        We Key by account_id because one client connection usually serves one account context
        (though cTrader API allows one connection to authorize multiple accounts, 
        our current adapter structure treats them 1:1).
        
        To be safe and support multi-account per connection in future, we could key by (host, port).
        But since `authorize_account` is stateful on the client (we just added _account_authorized flag),
        sharing a client across different accounts would require managing auth state per account.
        
        For now, 1 Connection per Account is safest and simplest given the previous refactor 
        (where we added `_account_authorized` bool to the client).
        """
        key = str(account_id)
        if key not in cls._clients:
            logger.info(f"Creating new persistent cTrader client for account {account_id}")
            client = AsyncCTraderClient(host, port)
            client.set_message_handler(_global_ctrader_handler)
            cls._clients[key] = client
        return cls._clients[key]

    @classmethod
    async def shutdown_all(cls):
        logger.info("Shutting down all cTrader connections...")
        for key, client in cls._clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client {key}: {e}")
        cls._clients.clear()
