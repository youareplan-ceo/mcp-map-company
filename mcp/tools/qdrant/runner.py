import os, json, uuid, re
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip()

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)

_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")

def _coerce_id(v: Any) -> str:
    """정수/UUID 문자열은 그대로, URL/임의 문자열은 UUID5로 안정 변환"""
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str) and _UUID_RE.match(v):
        return v
    if isinstance(v, str):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, v))
    return str(uuid.uuid4())

def _coerce_vector(v: Any) -> List[float]:
    """문자열(JSON/숫자열)→리스트 변환. 템플릿 미평가/실패 시 384차원 더미."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        t = v.strip()
        if t.startswith("{{") and t.endswith("}}"):
            return [0.0] * 384
        # JSON 배열
        if (t.startswith("[") and t.endswith("]")):
            try:
                parsed = json.loads(t)
                if isinstance(parsed, list):
                    return [float(x) for x in parsed]
            except Exception:
                pass
        # 쉼표/공백 구분 숫자열
        try:
            nums = [float(x) for x in re.split(r"[,\s]+", t.strip("[] ")) if x]
            if nums:
                return nums
        except Exception:
            pass
    # 마지막 안전망
    return [0.0] * 384

def _ensure_collection(coll: str, dim: int):
    """컬렉션 없으면 생성. 있으면 그대로 사용(불일치는 업서트에서 재생성)."""
    try:
        client.get_collection(coll)
        return
    except Exception:
        client.recreate_collection(
            collection_name=coll,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )

def _upsert_points(coll: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    qpoints: List[qm.PointStruct] = []
    for p in points:
        vec = _coerce_vector(p["vector"])
        pid = _coerce_id(p.get("id", str(uuid.uuid4())))
        qpoints.append(qm.PointStruct(id=pid, vector=vec, payload=p.get("payload", {})))

    dim = len(qpoints[0].vector) if isinstance(qpoints[0].vector, list) else 1

    try:
        _ensure_collection(coll, dim)
        client.upsert(collection_name=coll, points=qpoints)
    except Exception:
        # 차원 불일치 등으로 실패 시, 재생성 후 1회 재시도
        client.recreate_collection(
            collection_name=coll,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )
        client.upsert(collection_name=coll, points=qpoints)

    return {"status": "ok"}

def run(action: str, payload: Dict[str, Any]):
    payload = payload or {}

    if action == "upsert":
        coll = payload["collection"]
        pts  = payload.get("points")
        if pts is None and "point" in payload:
            pts = [payload["point"]]
        if not pts:
            return {"error": "missing points"}
        return _upsert_points(coll, pts)

    if action == "query":
        coll   = payload["collection"]
        vector = _coerce_vector(payload["vector"])
        limit  = int(payload.get("limit", 3))
        hits = client.search(
            collection_name=coll,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
        return {
            "hits": [
                {
                    "id": str(getattr(h, "id", "")),
                    "score": float(getattr(h, "score", 0.0)),
                    "payload": getattr(h, "payload", {}) or {},
                } for h in hits
            ]
        }

    return {"error": "unknown action"}
