import hmac
import hashlib
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HMACSigner:
    """
    Utility to generate and verify HMAC-SHA256 signatures for 3rd party API requests.
    Pattern: signature = hex(hmac_sha256(secret, timestamp + method + path + body))
    """

    @staticmethod
    def generate_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        Generates a signature for a request.
        """
        payload = f"{timestamp}{method.upper()}{path}{body}"
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(secret: str, signature: str, timestamp: str, method: str, path: str, body: str = "", window_seconds: int = 30) -> bool:
        """
        Verifies a signature with a timestamp window to prevent replay attacks.
        """
        # 1. Check Replay Attack Window
        try:
            ts_float = float(timestamp)
            now = time.time()
            if abs(now - ts_float) > window_seconds:
                logger.warning(f"HMAC Verification Failed: Timestamp outside window ({abs(now - ts_float):.1f}s)")
                return False
        except ValueError:
            return False

        # 2. Re-generate and Compare
        expected = HMACSigner.generate_signature(secret, timestamp, method, path, body)
        return hmac.compare_digest(expected, signature)

hmac_signer = HMACSigner()
