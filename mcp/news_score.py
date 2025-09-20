from time import time
from typing import Dict, Tuple

# 심볼별 뉴스 점수 캐시만 유지 (원문은 저장하지 않음)
_cache: Dict[str, Tuple[float, float]] = {}  # symbol -> (score, ts)

def get_news_score(symbol: str, ttl_sec: int = 3600) -> float:
    now = time()
    v = _cache.get(symbol.upper())
    if not v: 
        return 0.0
    score, ts = v
    return score if (now - ts) <= ttl_sec else 0.0

def upsert_news_score(symbol: str, score: float) -> None:
    _cache[symbol.upper()] = (float(score), time())
