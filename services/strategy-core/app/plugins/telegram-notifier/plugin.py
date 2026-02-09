import logging
import httpx
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from app.plugins.plugin_engine import BasePlugin
from app.database import SessionLocal

logger = logging.getLogger("telegram_notifier")

class TelegramNotifierPlugin(BasePlugin):
    """
    Sends signals and system notifications to a user-defined Telegram Bot.
    """
    def __init__(self, user_id: str, context: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(user_id, context, config)
        self.bot_token = self.config.get("token")
        self.chat_id = self.config.get("chat_id")
        self.enabled = bool(self.bot_token and self.chat_id)

    def activate(self):
        logger.info(f"Telegram Notifier activated for user {self.user_id}")

    def deactivate(self):
        logger.info(f"Telegram Notifier deactivated for user {self.user_id}")

    def register_hooks(self, hook_manager):
        if not self.enabled:
            logger.warning(f"Telegram Notifier for {self.user_id} is missing config. Hooks not registered.")
            return

        hook_manager.add_action("on_signal", self.on_signal_detected)
        hook_manager.add_action("notify_message", self.on_manual_message)

    async def on_signal_detected(self, signal: Dict[str, Any]):
        """
        Handle a new signal event.
        Payload: {id, symbol, direction, timeframe, price, reason, status, fund_id}
        """
        fund_id = signal.get("fund_id")
        if not fund_id:
            logger.debug("Signal missing fund_id, skipping Telegram notification.")
            return

        # Check if user belongs to this fund
        if not await self._is_user_in_fund(fund_id):
            logger.debug(f"User {self.user_id} does not have access to fund {fund_id}, skipping.")
            return

        # Format and send
        msg = self._format_signal_message(signal)
        await self._send_telegram(msg)

    async def on_manual_message(self, data: Dict[str, Any]):
        """
        Handle a manual notification request.
        Payload: {message, user_id, category}
        """
        target_user_id = data.get("user_id")
        # If user_id is provided, only notify if it matches this plugin instance
        if target_user_id and str(target_user_id) != str(self.user_id):
            return

        msg = data.get("message")
        if msg:
            await self._send_telegram(f"🔔 *System Notification*\n\n{msg}")

    async def _is_user_in_fund(self, fund_id: str) -> bool:
        """
        Verifies if the current plugin's user has access to this fund.
        Uses raw SQL because the model might be missing in strategy-core.
        """
        db = SessionLocal()
        try:
            # Check user_funds table
            query = text("SELECT 1 FROM user_funds WHERE user_id = :u AND fund_id = :f LIMIT 1")
            result = db.execute(query, {"u": self.user_id, "f": fund_id}).fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking user fund access: {e}")
            return False
        finally:
            db.close()

    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        symbol = signal.get("symbol", "Unknown")
        side = signal.get("direction", "Unknown").upper()
        price = signal.get("price", "N/A")
        tf = signal.get("timeframe", "N/A")
        reason = signal.get("reason", "No reason provided")
        
        emoji = "🚀" if side == "BUY" else "🔻"
        
        return (
            f"{emoji} *NEW SIGNAL DETECTED*\n\n"
            f"*Asset:* `{symbol}`\n"
            f"*Direction:* {side}\n"
            f"*Price:* `{price}`\n"
            f"*Timeframe:* `{tf}`\n\n"
            f"*Reason:* {reason}"
        )

    async def _send_telegram(self, message: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=5.0)
                if resp.status_code != 200:
                    logger.error(f"Telegram API Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
