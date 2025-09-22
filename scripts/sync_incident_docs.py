#!/usr/bin/env python3
import re, shutil, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "REPORTS" / "incident-center"
DST  = ROOT / "docs_site" / "docs" / "incident"
MKYML= ROOT / "docs_site" / "mkdocs.yml"

DST.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)

def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\-_. ]+", "", s)
    s = re.sub(r"\s+", "-", s)
    return s or "untitled"

# Create sample incident documents if REPORTS/incident-center is empty
if not any(SRC.rglob("*.md")):
    print("Creating sample incident documents...")

    # Create INDEX.md
    (SRC / "INDEX.md").write_text("""# Incident Center Index

인시던트 관리 센터 메인 페이지입니다.

## 최근 인시던트

- v1.0.1-pre 릴리스 관련 이슈들
- 시스템 안정성 개선 사항

## 문서 구조

- 각 버전별 폴더로 관리
- 완료 상태 및 요약 문서 포함
""", encoding="utf-8")

    # Create ENV_REQUIRED.md
    (SRC / "ENV_REQUIRED.md").write_text("""# 환경 변수 요구사항

인시던트 대응을 위한 필수 환경 변수입니다.

## 필수 변수

- `GITHUB_TOKEN`: GitHub API 접근용
- `SLACK_WEBHOOK`: 알림 발송용
- `DB_CONNECTION`: 데이터베이스 연결

## 설정 방법

```bash
export GITHUB_TOKEN="ghp_..."
export SLACK_WEBHOOK="https://hooks.slack.com/..."
```
""", encoding="utf-8")

# 소스 문서 수집 및 복사
docs = []
for p in sorted(SRC.rglob("*.md")):
    if p.name.startswith("_"):
        continue
    rel = p.relative_to(SRC)
    title = rel.stem.replace("_"," ").title()
    dst_name = f"{slugify(rel.stem)}.md"
    dst_path = DST / dst_name
    shutil.copy2(p, dst_path)
    docs.append({"title": title, "file": f"incident/{dst_name}"})
    print(f"  📄 {rel} → {dst_name}")

# mkdocs.yml 업데이트 (간단한 텍스트 조작)
if MKYML.exists():
    content = MKYML.read_text(encoding="utf-8")

    # Incident Center 섹션 구성
    ic_section = "  - Incident Center:\n    - Overview: incident/index.md\n"
    for doc in docs:
        ic_section += f"    - {doc['title']}: {doc['file']}\n"

    # 기존 nav에서 Incident Center 섹션 제거 후 추가
    lines = content.split('\n')
    new_lines = []
    skip_ic = False

    for line in lines:
        if '- Incident Center:' in line:
            skip_ic = True
            continue
        if skip_ic and line.startswith('    -'):
            continue
        if skip_ic and not line.startswith('    '):
            skip_ic = False

        if not skip_ic:
            new_lines.append(line)

    # nav 섹션에 Incident Center 추가
    nav_found = False
    final_lines = []
    for line in new_lines:
        final_lines.append(line)
        if line.strip() == 'nav:':
            nav_found = True
        elif nav_found and line.strip() and not line.startswith(' '):
            # nav 섹션 끝, Incident Center 추가
            final_lines.insert(-1, ic_section.rstrip())
            nav_found = False

    if nav_found:  # nav가 파일 끝까지 계속되는 경우
        final_lines.append(ic_section.rstrip())

    MKYML.write_text('\n'.join(final_lines), encoding="utf-8")
    print(f"  📝 Updated mkdocs.yml navigation")

print(f"✅ Synced {len(docs)} docs → {DST}")