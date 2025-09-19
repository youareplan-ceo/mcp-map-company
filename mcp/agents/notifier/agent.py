def run(task: str, ctx: dict):
    # 최소 스텁: 콘솔로 알림 흉내만 냄
    last = ctx or {}
    return {"agent":"notifier","task":task or "none","received":list(last.keys())}
