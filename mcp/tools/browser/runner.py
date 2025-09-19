import os, time, asyncio
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright
try:
    from readability import Document
except Exception:
    Document = None

# 단일 브라우저/페이지를 툴 수명 내 공유
_CTX = {"pw": None, "browser": None, "page": None}

def _ensure_ctx():
    if _CTX["pw"] is None:
        _CTX["pw"] = sync_playwright().start()
    if _CTX["browser"] is None:
        args = ["--disable-dev-shm-usage","--no-sandbox","--disable-gpu"]
        _CTX["browser"] = _CTX["pw"].chromium.launch(headless=True, args=args)
    if _CTX["page"] is None:
        _CTX["page"] = _CTX["browser"].new_page(user_agent="mcp-map/1.0 (+https://github.com/youareplan-ceo/mcp-map)")
    return _CTX["page"]

def _readability(html: str) -> str:
    if Document is None:
        return html
    try:
        doc = Document(html)
        return doc.summary(html_partial=True)
    except Exception:
        return html

def run(action: str, payload: dict):
    page = _ensure_ctx()
    payload = payload or {}

    if action == "open":
        url = payload.get("url")
        wait = payload.get("wait","domcontentloaded")
        timeout = int(payload.get("timeout_ms",20000))
        page.goto(url, wait_until=wait, timeout=timeout)
        return {"status":"ok", "url": url, "title": page.title()}

    if action == "extract":
        sel = payload.get("selector")
        mode = payload.get("mode","text")
        if sel:
            el = page.query_selector(sel)
            if not el:
                return {"content": ""}
            html = el.inner_html()
            txt  = el.inner_text()
        else:
            html = page.content()
            txt  = page.inner_text("body") if page.query_selector("body") else page.content()
        if mode == "html":
            return {"content": html}
        if mode == "readability":
            return {"content": _readability(html)}
        return {"content": txt}

    if action == "click":
        sel = payload.get("selector")
        wait_after = int(payload.get("wait_after_ms",500))
        page.click(sel, timeout=10000)
        time.sleep(wait_after/1000.0)
        return {"ok": True}

    if action == "type":
        sel   = payload.get("selector")
        text  = payload.get("text","")
        submit= bool(payload.get("submit", False))
        delay = int(payload.get("delay_ms", 20))
        page.fill(sel, "")
        page.type(sel, text, delay=delay)
        if submit:
            page.keyboard.press("Enter")
            time.sleep(0.7)
        return {"ok": True}

    if action == "screenshot":
        sel = payload.get("selector")
        path = payload.get("path","tmp/last_screenshot.png")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if sel:
            el = page.query_selector(sel)
            if not el:
                return {"path": ""}
            el.screenshot(path=path)
        else:
            page.screenshot(path=path, full_page=True)
        return {"path": path}

    if action == "close":
        try:
            if _CTX["page"]:
                _CTX["page"].close(); _CTX["page"]=None
            if _CTX["browser"]:
                _CTX["browser"].close(); _CTX["browser"]=None
            if _CTX["pw"]:
                _CTX["pw"].stop(); _CTX["pw"]=None
        except Exception:
            pass
        return {"ok": True}

    return {"error":"unknown action"}
