from typing import Dict
from dataclasses import dataclass

@dataclass
class LatencyState:
    ms: float
    order_mode: str  # SCALPING, LIMIT_ONLY

class LatencyAwareMonitor:
    """Monitors WebSocket Latency and adjust execution mode."""

    THRESHOLD_MS = 200 # Placeholder for image14 threshold

    def monitor(self, latency_ms: float) -> LatencyState:
        """
        Adjust execution logic based on latency:
        If latency > threshold, disable scalping and switch to Limit Orders.
        """
        if latency_ms > self.THRESHOLD_MS:
            return LatencyState(ms=latency_ms, order_mode="LIMIT_ONLY")
        return LatencyState(ms=latency_ms, order_mode="SCALPING")
