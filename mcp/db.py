from pathlib import Path
import duckdb

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'stockpilot.duckdb'

def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return duckdb.connect(str(DB_PATH))
