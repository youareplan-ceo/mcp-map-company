# 소스 레지스트리 필수 키 확인(얇은 구현)
from typing import List, Dict, Any

REQUIRED_BASE = ["id","name","type","cadence"]
REQUIRED_BY_TYPE = {
    "crawling": ["list_url"],
    "api": ["base_url"]
}

def _check_source(s: Dict[str, Any]) -> List[str]:
    errs = []
    for k in REQUIRED_BASE:
        if not s.get(k):
            errs.append(f"missing base key: {k}")
    t = s.get("type")
    for k in REQUIRED_BY_TYPE.get(t, []):
        if not s.get(k):
            errs.append(f"missing {t} key: {k}")
    return errs

def verify():
    try:
        from mcp.agents.policy_source_registry import load_sources
        sources = load_sources()
    except Exception as e:
        print(f"[validator] failed to load sources: {e}")
        return
    bad = 0
    for s in sources:
        errs = _check_source(s)
        if errs:
            bad += 1
            print(f"[validator] {s.get('id')} → WARN:", "; ".join(errs))
    if bad == 0:
        print(f"[validator] all {len(sources)} sources passed basic checks")
    else:
        print(f"[validator] {bad}/{len(sources)} sources need attention")
