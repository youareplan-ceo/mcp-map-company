import os, uuid, numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

PROVIDER = os.getenv("MEM_EMBEDDING_PROVIDER", "local").lower()
LOCAL_MODEL_NAME = os.getenv("MEM_LOCAL_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_MODEL     = os.getenv("MEM_EMBEDDING_MODEL", "text-embedding-3-large")

_local_model = None
_local_dim   = None
def _embed_local(text: str) -> np.ndarray:
    global _local_model, _local_dim
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(LOCAL_MODEL_NAME)
        _local_dim = _local_model.get_sentence_embedding_dimension()
    vec = _local_model.encode([text])[0].astype(np.float32)
    return vec

def _embed_openai(text: str) -> np.ndarray:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing for openai embedding")
    client = OpenAI(api_key=api_key)
    vec = client.embeddings.create(model=OPENAI_MODEL, input=text).data[0].embedding
    return np.array(vec, dtype=np.float32)

def _embed(text: str) -> np.ndarray:
    if PROVIDER == "local":
        return _embed_local(text)
    try:
        return _embed_openai(text)
    except Exception:
        return _embed_local(text)

def _dim() -> int:
    if PROVIDER == "local":
        global _local_dim
        if _local_dim is None:
            _ = _embed_local("dim-probe")
        return _local_dim or 384
    return len(_embed("dim-probe"))

# --- Qdrant 연결 ---
URL   = os.getenv("QDRANT_URL", "http://localhost:6333")
API   = os.getenv("QDRANT_API_KEY") or None
COL   = os.getenv("QDRANT_COLLECTION", "mcp_docs")
_client = QdrantClient(url=URL, api_key=API)

def _ensure_collection():
    dim = _dim()
    try:
        _client.get_collection(COL)
    except Exception:
        _client.recreate_collection(
            collection_name=COL,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )

def _coerce_id(doc_id: str):
    """Qdrant는 정수 또는 UUID만 허용.
       - 정수 문자열이면 int로
       - UUID 형식이면 UUID로
       - 그 외는 stable UUID5로 변환
    """
    s = str(doc_id).strip()
    if s.isdigit():
        return int(s)
    try:
        return str(uuid.UUID(s))  # 유효한 UUID면 그대로
    except Exception:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, s))  # 안정적 해시 UUID

def run(action: str, payload: dict):
    payload = payload or {}
    _ensure_collection()

    if action == "upsert":
        doc_id = str(payload.get("doc_id","")).strip()
        text   = str(payload.get("text","")).strip()
        if not doc_id or not text:
            return {"ok": False, "error": "doc_id/text required"}
        vec = _embed(text).tolist()
        qid = _coerce_id(doc_id)
        _client.upsert(
            collection_name=COL,
            points=[qm.PointStruct(id=qid, vector=vec, payload={"doc_id": doc_id, "text": text})],
        )
        return {"ok": True}

    if action == "query":
        text  = str(payload.get("text","")).strip()
        top_k = int(payload.get("top_k", 5))
        if not text:
            return {"hits":[]}
        qvec = _embed(text).tolist()
        res = _client.search(collection_name=COL, query_vector=qvec, limit=top_k, with_payload=True)
        hits = []
        for r in res:
            payload = r.payload or {}
            preview = (payload.get("text") or "")[:200]
            hits.append({"doc_id": payload.get("doc_id") or str(r.id), "score": float(r.score), "preview": preview})
        return {"hits": hits}

    if action == "delete":
        doc_id = str(payload.get("doc_id","")).strip()
        qid = _coerce_id(doc_id)
        _client.delete(collection_name=COL, points_selector=qm.PointIdsList(points=[qid]))
        return {"ok": True}

    if action == "reset":
        try:
            _client.delete_collection(COL)
        except Exception:
            pass
        _ensure_collection()
        return {"ok": True}

    return {"error": "unknown action"}
