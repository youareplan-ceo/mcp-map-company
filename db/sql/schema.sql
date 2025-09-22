-- Sprint-3 DB Schema (DuckDB)
PRAGMA disable_progress_bar;
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolios (
  portfolio_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS holdings (
  holding_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  qty DOUBLE NOT NULL,
  avg_price DOUBLE NOT NULL,
  as_of DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
  signal_id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  side TEXT CHECK (side IN ('BUY','SELL','HOLD')),
  strength DOUBLE,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
