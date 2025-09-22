#!/usr/bin/env python3
import os, re, sys
root = "."
md_files = []
for base, dirs, files in os.walk(root):
    if any(skip in base for skip in ["/.git", "/.worktrees", "/node_modules", "/tmp", "/REPORTS/incident-center/_SNAPSHOTS", "/REPORTS/incident-center/WEEKLY"]):
        continue
    for f in files:
        if f.endswith(".md"):
            md_files.append(os.path.join(base, f))

header_slug = lambda s: re.sub(r'[^a-z0-9\- ]+', '', s.strip().lower()).replace(' ', '-')
problems = []
for path in md_files:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
    except Exception as e:
        problems.append((path, f"read-fail: {e}")); continue
    # 수집: 헤더 앵커
    headers = [m.group(1) for m in re.finditer(r'^\s{0,3}#{1,6}\s+(.+?)\s*$', txt, re.M)]
    anchors = set("#" + header_slug(h) for h in headers)
    # 내부 앵커 링크 검사
    for m in re.finditer(r'\]\((#[^)]+)\)', txt):
        if m.group(1) not in anchors:
            problems.append((path, f"missing-anchor:{m.group(1)}"))

    # 상대경로(.md) 존재 여부 간단 확인
    for m in re.finditer(r'\]\(((?!https?://)[^)]+\.md)(#[^)]+)?\)', txt):
        target = os.path.normpath(os.path.join(os.path.dirname(path), m.group(1)))
        if not os.path.exists(target):
            problems.append((path, f"missing-file:{m.group(1)}"))

# 출력
print("# Anchors/Links quick report")
print(f"- scanned: {len(md_files)} files")
print(f"- issues : {len(problems)}")
for p, msg in problems[:200]:
    print(f"{p}: {msg}")
# 문서 작업 방해하지 않도록 항상 0 반환
sys.exit(0)
