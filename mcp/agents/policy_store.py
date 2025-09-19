# policy_store.py — 저장 레이어(얇은 구현: 경로 확인 + 로그)
import pathlib, yaml, json

def persist():
    cfg_path = pathlib.Path("config/db.yaml")
    schema_path = pathlib.Path("duckdb/schema.sql")
    norm_path = pathlib.Path("db/policies_normalized.json")

    db_path = "(unknown)"
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            db_path = cfg.get("db_path") or db_path
        except Exception as e:
            print(f"[store] failed to read db.yaml: {e}")

    if not norm_path.exists():
        norm_path.parent.mkdir(parents=True, exist_ok=True)
        norm_path.write_text("[]", encoding="utf-8")

    try:
        items = json.loads(norm_path.read_text(encoding='utf-8') or "[]")
        n = len(items)
    except Exception as e:
        print(f"[store] failed to read normalized file: {e}")
        n = 0

    print(f"[store] target_db={db_path} ; schema={schema_path.exists()} ; items={n}")
    print("[store] DRY: no DB writes yet. (later: connect + apply schema + upsert)")
