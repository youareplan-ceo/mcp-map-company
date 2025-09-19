import os, duckdb, numpy as np

DB_PATH = os.path.expanduser(os.getenv("MEM_DB_PATH", "data/memory.duckdb"))
PROVIDER = os.getenv("MEM_EMBEDDING_PROVIDER", "openai").lower()
LOCAL_MODEL_NAME = os.getenv("MEM_LOCAL_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_MODEL = os.getenv("MEM_EMBEDDING_MODEL", "text-embedding-3-large")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
con = duckdb.connect(DB_PATH)
con.execute("""
CREATE TABLE IF NOT EXISTS docs(
  doc_id TEXT PRIMARY KEY,
  text   TEXT,
  embedding BLOB
);
""")

_local_model = None
def _embed_local(text: str):
  global _local_model
  if _local_model is None:
    from sentence_transformers import SentenceTransformer
    _local_model = SentenceTransformer(LOCAL_MODEL_NAME)
  vec = _local_model.encode([text])[0].astype(np.float32)
  return vec

def _embed_openai(text: str):
  from openai import OpenAI
  api_key = os.getenv("OPENAI_API_KEY")
  if not api_key:
    raise RuntimeError("OPENAI_API_KEY missing in config/.env")
  client = OpenAI(api_key=api_key)
  vec = client.embeddings.create(model=OPENAI_MODEL, input=text).data[0].embedding
  return np.array(vec, dtype=np.float32)

def _embed(text: str):
  if PROVIDER == "local":
    return _embed_local(text)
  # 기본은 openai, 429 등 오류 시 로컬로 폴백
  try:
    return _embed_openai(text)
  except Exception as e:
    # 폴백 허용
    try:
      return _embed_local(text)
    except Exception:
      raise e

def _cosine(a: np.ndarray, b: np.ndarray):
  denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
  return float(np.dot(a, b) / denom)

def run(action: str, payload: dict):
  payload = payload or {}
  if action == "upsert":
    doc_id = payload.get("doc_id","").strip()
    text   = payload.get("text","").strip()
    if not doc_id or not text:
      return {"ok": False, "error":"doc_id/text required"}
    emb = _embed(text)
    con.execute("DELETE FROM docs WHERE doc_id = ?", [doc_id])
    con.execute("INSERT INTO docs(doc_id, text, embedding) VALUES (?, ?, ?)", [doc_id, text, emb.tobytes()])
    return {"ok": True}

  if action == "query":
    query_text = payload.get("text","").strip()
    top_k = int(payload.get("top_k", 5))
    if not query_text:
      return {"hits":[]}
    q = _embed(query_text)
    rows = con.execute("SELECT doc_id, text, embedding FROM docs").fetchall()
    scored = []
    for doc_id, text, blob in rows:
      emb = np.frombuffer(blob, dtype=np.float32)
      scored.append((doc_id, _cosine(q, emb), text))
    scored.sort(key=lambda x: x[1], reverse=True)
    hits = [{"doc_id":d, "score":float(s), "preview": (t[:200] if t else "")} for d,s,t in scored[:top_k]]
    return {"hits": hits}

  if action == "delete":
    doc_id = payload.get("doc_id","").strip()
    con.execute("DELETE FROM docs WHERE doc_id = ?", [doc_id])
    return {"ok": True}

  if action == "reset":
    con.execute("DELETE FROM docs")
    return {"ok": True}

  return {"error":"unknown action"}
