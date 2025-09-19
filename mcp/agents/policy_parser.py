# policy_parser.py — 원시→정규화(얇은 구현: 자리 보장 + 로그)
import json, pathlib

def parse():
    raw_path = pathlib.Path("raw_data/policies.json")
    norm_path = pathlib.Path("db/policies_normalized.json")
    norm_path.parent.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        print(f"[parse] missing raw file: {raw_path} → creating empty []")
        raw_items = []
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("[]", encoding="utf-8")
    else:
        try:
            raw_items = json.loads(raw_path.read_text(encoding="utf-8") or "[]")
        except Exception as e:
            print(f"[parse] failed to read raw: {e} → treating as []")
            raw_items = []

    # 아직 정규화 로직 없음: 빈 배열로 보존
    if not norm_path.exists():
        norm_path.write_text("[]", encoding="utf-8")

    print(f"[parse] raw_items={len(raw_items)} ; normalized_file={norm_path} (DRY: no transform yet)")
