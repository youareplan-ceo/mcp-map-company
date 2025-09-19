# mcp/run.py
"""
Thin MCP Flow Runner + FastAPI health (Render entrypoint)

- .flow(YAML) 파일을 읽고 steps를 순서대로 실행하는 매우 단순한 러너
- FastAPI `app` 을 함께 노출하여 Render(uvicorn)가 찾을 수 있게 함
"""

from __future__ import annotations
import argparse
import importlib
import pathlib
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI

# -----------------------------
# FastAPI (Render entrypoint)
# -----------------------------
app = FastAPI(title="mcp-map-company", version="0.1.0")

@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}

# -----------------------------
# Flow runner (very thin)
# -----------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]   # 프로젝트 루트: ~/Desktop/mcp-map-company
FLOWS_DIR = ROOT / "mcp" / "flows"                   # 플로우 디렉터리
AGENTS_PKG = "mcp.agents"                            # 에이전트 모듈 패키지 prefix

def load_flow(flow_name: str) -> Dict[str, Any]:
    """
    mcp/flows/<flow_name>.flow YAML을 로드
    """
    path = FLOWS_DIR / f"{flow_name}.flow"
    if not path.exists():
        raise FileNotFoundError(f"Flow not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _run_agent_step(step: Dict[str, Any]) -> None:
    """
    step 예시:
      - agent: stockpilot
        task: research
        args: { symbols: ["AAPL","TSLA"] }
    """
    agent_name = step.get("agent")
    task_name  = step.get("task")
    args       = step.get("args", {}) or {}

    if not agent_name or not task_name:
        raise ValueError(f"Invalid agent step: {step}")

    module_name = f"{AGENTS_PKG}.{agent_name}"
    mod = importlib.import_module(module_name)
    if not hasattr(mod, task_name):
        raise AttributeError(f"{module_name}.{task_name}() not found")

    fn = getattr(mod, task_name)
    result = fn(**args) if args else fn()
    print(f"[agent:{agent_name}.{task_name}] -> {result}")

def _run_gate_step(step: Dict[str, Any]) -> None:
    """
    step 예시:
      - gate: manual_approval
    (여기서는 데모로 통과만)
    """
    name = step.get("gate")
    print(f"[gate:{name}] pass (demo)")

def _run_flow_step(step: Dict[str, Any], depth: int, max_depth: int) -> None:
    """
    step 예시:
      - flow: sub_flow_name
    """
    name = step.get("flow")
    if depth >= max_depth:
        raise RecursionError(f"Max flow depth exceeded: {name}")
    print(f"[flow:{name}] enter depth={depth+1}")
    run_flow(name, depth=depth+1, max_depth=max_depth)

def run_flow(flow_name: str, *, depth: int = 0, max_depth: int = 3) -> None:
    spec = load_flow(flow_name)
    steps: List[Dict[str, Any]] = spec.get("steps", [])
    print(f"[flow:{flow_name}] steps={len(steps)}")

    for step in steps:
        if "agent" in step:
            _run_agent_step(step)
        elif "gate" in step:
            _run_gate_step(step)
        elif "flow" in step:
            _run_flow_step(step, depth, max_depth)
        else:
            raise ValueError(f"Unknown step type: {step}")

def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Thin MCP Flow Runner")
    parser.add_argument("flow", help="flow name (without .flow)")
    parser.add_argument("--max-depth", type=int, default=3, help="sub-flow recursion limit")
    args = parser.parse_args(argv)

    run_flow(args.flow, max_depth=args.max_depth)

if __name__ == "__main__":
    main()
