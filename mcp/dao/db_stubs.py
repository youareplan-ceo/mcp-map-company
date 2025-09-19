"""
DuckDB DAO Stubs — 실제 DB작업은 나중에.
지금은 함수 시그니처와 주석, TODO만 둡니다.
"""

from typing import List, Dict, Any

def connect_duckdb(db_path: str):
    """
    TODO: duckdb.connect(db_path) 로 실제 연결
    현재는 None 반환(뼈대)
    """
    return None

def apply_schema(conn, schema_sql_path: str):
    """
    TODO: schema.sql 읽어서 conn.execute()로 적용
    현재는 DRY-RUN 용 주석만
    """
    pass

def upsert_policies(conn, policies: List[Dict[str, Any]]):
    """TODO: policies 테이블 upsert (program_id PK)"""
    pass

def upsert_applicants(conn, applicants: List[Dict[str, Any]]):
    """TODO: applicants 테이블 upsert (applicant_id PK)"""
    pass

def upsert_matches(conn, matches: List[Dict[str, Any]]):
    """TODO: matches 테이블 upsert (applicant_id, program_id PK)"""
    pass

def upsert_scores(conn, scores: List[Dict[str, Any]]):
    """TODO: scores 테이블 upsert (applicant_id, program_id PK)"""
    pass
