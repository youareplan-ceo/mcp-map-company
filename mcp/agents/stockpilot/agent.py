def run(task: str, ctx: dict):
    # 최소 스텁: 리서치/요약 등 태스크 이름만 로그로 반환
    return {"agent":"stockpilot","task":task or "none","ctx_keys":list((ctx or {}).keys())}
