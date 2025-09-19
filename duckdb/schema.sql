-- 뼈대용 DDL (실행은 나중에)
CREATE TABLE IF NOT EXISTS policies (
  program_id TEXT PRIMARY KEY,
  name TEXT,
  agency TEXT,
  region TEXT,
  industry_code TEXT,
  limit_max BIGINT,
  interest_rate_max DOUBLE,
  raw JSON
);

CREATE TABLE IF NOT EXISTS applicants (
  applicant_id TEXT PRIMARY KEY,
  company_name TEXT,
  region TEXT,
  industry_code TEXT,
  biz_age_months INTEGER,
  revenue_last12m BIGINT,
  credit_band TEXT,
  tax_arrears_flag BOOLEAN,
  special_flags JSON
);

CREATE TABLE IF NOT EXISTS matches (
  applicant_id TEXT,
  program_id TEXT,
  eligible BOOLEAN,
  reasons JSON,
  PRIMARY KEY (applicant_id, program_id)
);

CREATE TABLE IF NOT EXISTS scores (
  applicant_id TEXT,
  program_id TEXT,
  score INTEGER,
  notes JSON,
  PRIMARY KEY (applicant_id, program_id)
);
