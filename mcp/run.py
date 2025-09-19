"""
Thin MCP Flow Runner (skeleton)
- .flow(YAML) 파일을 읽고, steps를 순서대로 실행
- agent step: mcp.agents.<agent> 모듈 import 후 <task>() 함수가 있으면 호출
- flow step: 하위 flow 재귀 실행(깊이 제한)
"""
import argparse, importlib, sys, pathlib
from typing import Any, Dict, List
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]  # 프로젝트 루트 (~/Desktop/mcp-map)
FLOWS_DIR = ROOT / "mcp" / "flows"

def load_flow(flow_name: str) -> Dict[str, Any]:
    path = FLOWS_DIR / f"{flow_name}.flow"
    if not path.exists():
        raise FileNotFoundError(f"Flow not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_flow(flow_name: str, dry: bool=False, depth: int=0, max_depth: int=5):
    if depth > max_depth:
        print(f"[WARN] Max depth reached at flow={flow_name}")
        return
    flow = load_flow(flow_name)
    steps: List[Dict[str, Any]] = flow.get("steps", [])
    print(f"[FLOW] {flow.get('name', flow_name)}  (steps={len(steps)})")

    for i, step in enumerate(steps, 1):
        if "agent" in step:
            agent = step["agent"]
            task  = step.get("task", "run")
            print(f"  [{i}/{len(steps)}] AGENT {agent}.{task}()")
            if dry:
                print("    → DRY-RUN: skip execution")
                continue
            try:
                mod = importlib.import_module(f"mcp.agents.{agent}")
                fn  = getattr(mod, task, None)
                if callable(fn):
                    fn()
                    print("    ✓ executed")
                else:
                    print("    ⚠ function not found; SKIP")
            except Exception as e:
                print(f"    ✗ error: {e}")
                raise
        elif "flow" in step:
            sub = step["flow"]
            print(f"  [{i}/{len(steps)}] FLOW {sub}")
            run_flow(sub, dry=dry, depth=depth+1, max_depth=max_depth)
        else:
            print(f"  [{i}/{len(steps)}] ? unknown step: {step}")

def main():
    ap = argparse.ArgumentParser(description="MCP thin flow runner (skeleton)")
    ap.add_argument("flow", help="flow name without extension (e.g. policy_sources_verify)")
    ap.add_argument("--dry", action="store_true", help="print only; do not execute")
    args = ap.parse_args()
    run_flow(args.flow, dry=args.dry)

if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))  # mcp 패키지 import용
    main()
