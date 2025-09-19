import os, json, sys
import urllib.request

def run(action, payload):
    """
    action: summary_to_slack | print
    payload: {"text": "..."} 또는 {"hits": [...]} 등 임의 컨텍스트
    """
    text = payload.get("text")
    if not text and "hits" in payload:
        # qdrant 검색결과 요약형 출력
        lines = []
        for h in payload["hits"][:5]:
            pl = h.get("payload", {})
            lines.append(f"- {pl.get('title','')} {pl.get('url','')}".strip())
        text = "검색결과 요약:\n" + "\n".join(lines) if lines else json.dumps(payload, ensure_ascii=False)

    if not text:
        text = json.dumps(payload, ensure_ascii=False)

    if action == "summary_to_slack":
        webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        if webhook:
            try:
                data = json.dumps({"text": text}).encode("utf-8")
                req = urllib.request.Request(webhook, data=data, headers={"Content-Type":"application/json"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    r.read()
                return {"status":"sent"}
            except Exception as e:
                return {"status":"error","error":str(e),"fallback_print":text}
        # 키 없으면 콘솔로
        print(text)
        return {"status":"printed"}

    # 기본은 콘솔 프린트
    print(text)
    return {"status":"printed"}
