import logging

logger = logging.getLogger(__name__)

class TokenMonitor:
    """
    Estimates token usage and provides saturation triggers for
    Token-Aware Routing.
    """
    
    # 1M token limit for Flash Lite 2.0
    # Safe threshold to trigger "Slim Mode"
    SOFT_LIMIT_TOKEN = 15000 
    HARD_LIMIT_TOKEN = 25000
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Inexpensive estimation based on char-to-token ratio (~3.5 chars/token).
        """
        if not text:
            return 0
        return len(text) // 3
    
    @classmethod
    def is_saturated(cls, scratchpad_text: str) -> bool:
        """
        Returns True if the current reasoning context is nearing thresholds.
        """
        estimated = cls.estimate_tokens(scratchpad_text)
        saturated = estimated > cls.SOFT_LIMIT_TOKEN
        if saturated:
            logger.warning(f"⚠️ Context Saturation Detected: {estimated} tokens. Recommending SLIM data mode.")
        return saturated
