import logging
import httpx
import html
import re
import traceback
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """Escape basic HTML special characters."""
    return html.escape(text, quote=False)

def markdown_to_html(text: str) -> str:
    """
    Convert basic Markdown to Telegram-compatible HTML.
    Handles: bold, italic, inline code, and detects tables for monospace.
    """
    # 1. Escape special HTML characters first
    text = escape_html(text)
    
    # 2. Extract code blocks and tables to protect them from other formatting
    placeholders = {}
    
    # Helper to protect blocks
    def protect(content, tag="pre"):
        idx = len(placeholders)
        key = f"__BLOCK_{idx}__"
        placeholders[key] = f"<{tag}>{content.strip()}</{tag}>"
        return key

    # Protect code blocks: ```block``` -> <pre>block</pre>
    text = re.sub(r'```(.*?)```', lambda m: protect(m.group(1)), text, flags=re.DOTALL)

    # Protect Markdown/ASCII tables
    lines = text.split('\n')
    processed_lines = []
    current_table = []
    has_separator = False
    
    for line in lines:
        # Detect standard Markdown or Tabulate (psql/grid) tables
        is_table_row = '|' in line or (line.startswith('+') and '-' in line)
        
        if is_table_row:
            current_table.append(line)
            if re.search(r'\|[:\-\s]+\|', line) or (line.startswith('+') and '-' in line):
                has_separator = True
        else:
            if current_table:
                if has_separator and len(current_table) >= 2:
                    processed_lines.append(protect("\n".join(current_table)))
                else:
                    processed_lines.extend(current_table)
                current_table = []
                has_separator = False
            processed_lines.append(line)
            
    if current_table:
        if has_separator or len(current_table) > 1:
            processed_lines.append(protect("\n".join(current_table)))
        else:
            processed_lines.extend(current_table)
    
    text = "\n".join(processed_lines)

    # 3. Apply inline formatting to NON-PROTECTED text
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)

    # 4. Restore protected blocks
    for key, val in placeholders.items():
        text = text.replace(key, val)
    
    return text

async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_to_message_id: Optional[int] = None,
    message_thread_id: Optional[int] = None
) -> bool:
    """
    Send a message to Telegram with automatic error handling and retries.
    """
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            return False
        
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Telegram message limit is 4096 characters
        MAX_LENGTH = 4096
        if len(text) > MAX_LENGTH:
            logger.warning(f"Message too long ({len(text)} chars), truncating")
            text = text[:MAX_LENGTH-50] + "\n\n...(truncated)"
        
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        if parse_mode == "HTML":
            payload["text"] = markdown_to_html(text)
            payload["parse_mode"] = "HTML"
        elif parse_mode == "Markdown":
            payload["parse_mode"] = "Markdown"
            
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            
        if message_thread_id:
            payload["message_thread_id"] = message_thread_id
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(telegram_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent to {chat_id}")
                return True
            
            error_detail = response.json()
            logger.error(f"❌ Telegram API error {response.status_code}: {error_detail}")
            
            if parse_mode and "can't parse" in str(error_detail).lower():
                return await send_telegram_message(
                    chat_id, text, parse_mode=None, 
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id
                )
            
            if reply_to_message_id and "message to be replied not found" in str(error_detail).lower():
                return await send_telegram_message(
                    chat_id, text, parse_mode=parse_mode, 
                    reply_to_message_id=None,
                    message_thread_id=message_thread_id
                )
            
            return False
            
    except Exception as e:
        logger.error(f"💥 Failed to send Telegram message: {e}")
        return False
