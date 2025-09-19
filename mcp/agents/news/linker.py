import json, re, yaml
from pathlib import Path

PARSED = Path("db/news_parsed.json")
ALIA   = Path("schemas/stocks/aliases.yaml")
LINKED = Path("db/news_by_symbol.json"); LINKED.parent.mkdir(parents=True, exist_ok=True)

def _load_aliases():
    alias = {}
    if ALIA.exists():
        try:
            a = yaml.safe_load(ALIA.read_text(encoding="utf-8")) or {}
            alias = a.get("aliases", {}) or {}
        except Exception:
            pass
    return alias

def _hits(text, terms):
    if not text or not terms: return 0
    s = text.lower()
    cnt = 0
    for t in terms:
        t = (t or "").strip()
        if not t: 
            continue
        if re.search(r'\b'+re.escape(t.lower())+r'\b', s):
            cnt += 1
    return cnt

def link():
    alias = _load_aliases()
    try:
        parsed = json.loads(PARSED.read_text(encoding="utf-8") or "[]")
    except Exception:
        parsed = []

    out = []
    for a in parsed:
        text = (a.get("title") or "") + " " + (a.get("desc") or "")
        best, best_hits = None, 0
        sym_hint = a.get("_sym_query")

        candidates = list(alias.keys())
        if sym_hint and sym_hint not in candidates:
            candidates.insert(0, sym_hint)

        for sym in candidates:
            terms = [sym] + (alias.get(sym, []))
            h = _hits(text, terms)
            if h > best_hits:
                best_hits = h
                best = sym

        out.append({
            "symbol": best or sym_hint,
            "hits": best_hits,
            "title": a.get("title"),
            "url": a.get("url"),
            "source": a.get("source"),
            "publishedAt": a.get("publishedAt"),
        })

    LINKED.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[news.link] linked={len(out)} -> {LINKED}")
