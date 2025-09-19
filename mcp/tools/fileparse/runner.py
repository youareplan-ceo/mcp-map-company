import os, subprocess
from pathlib import Path
from pdfminer.high_level import extract_text
from docx import Document

def _parse_pdf(path, max_chars=5000):
    try:
        txt = extract_text(path)
        return txt[:max_chars]
    except Exception as e:
        return f"[PDF parse error] {e}"

def _parse_docx(path, max_chars=5000):
    try:
        doc = Document(path)
        txt = "\n".join(p.text for p in doc.paragraphs)
        return txt[:max_chars]
    except Exception as e:
        return f"[DOCX parse error] {e}"

def _parse_hwp(path, max_chars=5000):
    try:
        # pypandoc 통해 텍스트 추출 시도
        txt = subprocess.check_output(["pandoc", "-t", "plain", path], text=True)
        return txt[:max_chars]
    except Exception as e:
        return f"[HWP parse error] {e}"

def run(action: str, payload: dict):
    if action != "parse":
        return {"error":"unknown action"}
    path = payload.get("path")
    if not path or not os.path.exists(path):
        return {"text": "[error] file not found"}
    max_chars = int(payload.get("max_chars",5000))
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        txt = _parse_pdf(path,max_chars)
    elif ext == ".docx":
        txt = _parse_docx(path,max_chars)
    elif ext == ".hwp":
        txt = _parse_hwp(path,max_chars)
    else:
        try:
            txt = Path(path).read_text()[:max_chars]
        except Exception as e:
            txt = f"[raw read error] {e}"
    return {"text": txt}
