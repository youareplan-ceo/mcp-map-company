from dataclasses import dataclass
from typing import List
@dataclass
class Signal:
    ticker: str
    action: str   # BUY|SELL|HOLD
    confidence: float
    horizon: str  # D|W|M
    reasons: List[str]
