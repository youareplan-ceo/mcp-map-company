import duckdb, pathlib, pandas as pd, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "mcp.duckdb"
CSV = ROOT / "data" / "sample" / "holdings.csv"

DB.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB))

# 스키마 생성 (기존 테이블 존재시 스킵)
con.execute("""
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
con.execute("""
CREATE TABLE IF NOT EXISTS portfolios (
  portfolio_id TEXT PRIMARY KEY,
  user_id TEXT,
  name TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
con.execute("""
CREATE TABLE IF NOT EXISTS holdings (
  holding_id BIGINT PRIMARY KEY,
  portfolio_id TEXT,
  symbol TEXT,
  qty DOUBLE,
  avg_price DOUBLE,
  as_of DATE
);
""")

# 샘플 데이터 보강(있으면 유지)
con.execute("INSERT OR IGNORE INTO users (user_id) VALUES ('U001');")
con.execute("INSERT OR IGNORE INTO portfolios (portfolio_id, user_id, name) VALUES ('P001','U001','Main'),('P002','U001','Side');")

# CSV 있으면 로드, 없으면 데모 프레임 생성
if CSV.exists():
    df = pd.read_csv(CSV)
else:
    df = pd.DataFrame([
        {"portfolio_id":"P001","symbol":"AAPL","qty":10,"avg_price":180.5,"as_of":"2025-09-20"},
        {"portfolio_id":"P001","symbol":"MSFT","qty":7,"avg_price":410.0,"as_of":"2025-09-20"},
    ])

# 기존 데이터와 중복 최소화를 위해 upsert 유사 처리(간단히 append 후 dedup)
tmp = "holdings_tmp"
con.execute(f"CREATE OR REPLACE TABLE {tmp} (portfolio_id TEXT, symbol TEXT, qty DOUBLE, avg_price DOUBLE, as_of TEXT);")
con.register("df", df)
con.execute(f"INSERT INTO {tmp} SELECT portfolio_id, symbol, qty, avg_price, as_of FROM df;")
con.execute("""
INSERT INTO holdings (holding_id, portfolio_id, symbol, qty, avg_price, as_of)
SELECT
  'H' || (row_number() OVER () + COALESCE((SELECT COUNT(*) FROM holdings), 0)),
  portfolio_id, symbol, qty, avg_price, CAST(as_of AS DATE)
FROM holdings_tmp;
""")
con.execute("DROP TABLE holdings_tmp;")

print("✅ Ingested rows:", len(df))
con.close()
