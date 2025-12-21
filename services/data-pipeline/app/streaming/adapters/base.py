from abc import ABC, abstractmethod
from typing import List, Callable, Awaitable

class StreamAdapter(ABC):
    def __init__(self, callback: Callable[[dict], Awaitable[None]]):
        self.callback = callback

    @abstractmethod
    async def start(self, instruments: List[str]):
        """Start streaming the given instruments."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop streaming."""
        pass
