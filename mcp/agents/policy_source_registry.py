# 읽기 전용 레지스트리 로더(얇은 구현)
import yaml, pathlib

def load_sources():
    path = pathlib.Path("schemas/policy_sources.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    print(f"[registry] loaded {len(sources)} sources")
    for s in sources[:3]:
        print("  -", s.get("id"), "/", s.get("name"))
    return sources
