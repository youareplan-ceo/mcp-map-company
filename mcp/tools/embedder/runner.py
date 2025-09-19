from sentence_transformers import SentenceTransformer
_model = None
def _get():
    global _model
    if _model is None:
        # 경량 & 한글도 무난한 범용기
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def run(action: str, payload: dict):
    if action != "encode":
        return {"error":"unknown action"}
    text = (payload or {}).get("text","").strip()
    if not text:
        return {"vector":[]}
    m = _get()
    vec = m.encode(text).tolist()
    return {"vector": vec}
