import re, requests
from html import unescape

def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE|re.DOTALL)
    return unescape(m.group(1).strip()) if m else ""

def _extract_text(html: str, limit: int = 1200) -> str:
    # 태그 제거 후 공백 정리 (간단 파서)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return unescape(text)[:limit]

def run(action: str, payload: dict):
    payload = payload or {}
    if action not in ("fetch", "get"):
        return {"error": "unknown action"}

    url = payload.get("url")
    if not url:
        return {"error": "missing url"}

    # 간단 fetch
    resp = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0 MCP-Webfetch"})
    resp.raise_for_status()
    html = resp.text

    title = _extract_title(html)
    text  = _extract_text(html, limit=4000)
    snippet = text[:280]

    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "content": text,
    }
