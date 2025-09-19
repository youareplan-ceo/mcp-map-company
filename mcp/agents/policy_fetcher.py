# policy_fetcher.py — 원시 공고 수집(얇은 구현: 자리 보장 + 로그)
import json, pathlib
from datetime import datetime

def fetch():
    try:
        from mcp.agents.policy_source_registry import load_sources
        sources = load_sources() or []
    except Exception as e:
        print(f"[fetch] failed to load sources: {e}")
        sources = []

    raw_path = pathlib.Path("raw_data/policies.json")
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 없으면 빈 배열 생성
    if not raw_path.exists():
        raw_path.write_text("[]", encoding="utf-8")
        created = True
    else:
        created = False

    print(f"[fetch] sources={len(sources)} ; raw_file={'created' if created else 'exists'} → {raw_path}")
    print("[fetch] DRY: no network. (later: crawl/api and append raw items)")
    # 참고: 이후 실제 구현에서 raw 항목 append 예정
