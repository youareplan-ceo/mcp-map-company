import os, textwrap
from typing import Dict, Any

def _local_summarize(title: str, content: str) -> str:
    content = (content or "")[:1200]
    # 아주 단순한 규칙 기반 요약 (키 없을 때 폴백)
    first = content.split("\n")[0][:180]
    bullet = []
    for line in content.splitlines():
        line=line.strip()
        if 30 < len(line) < 120 and line.endswith("."):
            bullet.append("• " + line)
        if len(bullet) >= 4:
            break
    return textwrap.dedent(f"""\
    [{title}]
    핵심 요약: {first}
    포인트:
    {chr(10).join(bullet) if bullet else "• (요약 포인트 부족)"}
    """)

def run(action: str, payload: Dict[str, Any]):
    """
    action: summarize
    payload: {"title": str, "content": str}
    """
    title = payload.get("title","")
    content = payload.get("content","")

    # 키가 있으면 LLM 호출 (간단 가드만, 실제 프롬프트는 추후 고도화)
    oai = os.getenv("OPENAI_API_KEY","").strip()
    claude = os.getenv("ANTHROPIC_API_KEY","").strip()

    if action == "summarize":
        if oai or claude:
            try:
                # 우선 OpenAI가 있으면 OpenAI, 없으면 Claude 사용
                if oai:
                    from openai import OpenAI
                    client = OpenAI()
                    prompt = f"제목: {title}\n\n다음 텍스트를 한국어로 6줄 이내 핵심 요약과 3개 불릿 포인트로 요약해줘:\n\n{content[:4000]}"
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.2,
                    )
                    summary = res.choices[0].message.content
                else:
                    import anthropic
                    client = anthropic.Anthropic()
                    prompt = f"제목: {title}\n\n다음 텍스트를 한국어로 6줄 이내 핵심 요약과 3개 불릿 포인트로 요약:\n\n{content[:4000]}"
                    msg = client.messages.create(
                        model="claude-3-5-sonnet-latest",
                        max_tokens=600,
                        messages=[{"role":"user","content":prompt}],
                    )
                    summary = "".join([b.text for b in msg.content if getattr(b, "type", "")=="text"])
                return {"summary": summary.strip()}
            except Exception as e:
                # 실패 시 폴백
                return {"summary": _local_summarize(title, content), "warning": str(e)}
        # 키 없으면 폴백
        return {"summary": _local_summarize(title, content)}

    return {"error":"unknown action"}
