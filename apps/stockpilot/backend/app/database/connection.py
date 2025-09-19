"""
데이터베이스 연결 및 세션 관리
SQLAlchemy를 사용한 PostgreSQL 데이터베이스 연결 설정
"""

import logging
import time
from datetime import datetime
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

logger = logging.getLogger(__name__)

# 환경변수에서 데이터베이스 설정 가져오기
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stockpilot_db")
DB_USER = os.getenv("DB_USER", "stockpilot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 데이터베이스 URL 생성
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=300,    # 5분마다 연결 재사용
    echo=False,          # SQL 로그 출력 (개발시에만 True)
)

# 세션 로컬 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base 클래스 생성
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션을 생성하고 반환하는 의존성 함수
    FastAPI의 Depends에서 사용
    
    Yields:
        Session: 데이터베이스 세션
    """
    db = SessionLocal()
    try:
        logger.debug("데이터베이스 세션 생성")
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 세션 오류: {str(e)}")
        db.rollback()
        raise
    finally:
        logger.debug("데이터베이스 세션 종료")
        db.close()


def create_tables():
    """
    모든 테이블을 생성
    애플리케이션 시작 시 호출
    """
    try:
        logger.info("데이터베이스 테이블 생성 중...")
        
        # models 모듈 import (테이블 정의 로드)
        from ..models import stock
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        logger.info("데이터베이스 테이블 생성 완료")
        
    except Exception as e:
        logger.error(f"테이블 생성 실패: {str(e)}")
        raise


def check_database_connection() -> bool:
    """
    데이터베이스 연결 상태 확인
    
    Returns:
        bool: 연결 성공 여부
    """
    try:
        with engine.connect() as connection:
            # 간단한 쿼리 실행
            result = connection.execute("SELECT 1")
            result.fetchone()
            
        logger.info("데이터베이스 연결 확인 성공")
        return True
        
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {str(e)}")
        return False


def get_database_info() -> dict:
    """
    데이터베이스 정보 반환
    
    Returns:
        dict: 데이터베이스 정보
    """
    try:
        with engine.connect() as connection:
            # PostgreSQL 버전 조회
            version_result = connection.execute("SELECT version()")
            version = version_result.fetchone()[0]
            
            # 현재 데이터베이스 이름 조회
            db_result = connection.execute("SELECT current_database()")
            current_db = db_result.fetchone()[0]
            
            # 연결 수 조회
            conn_result = connection.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            active_connections = conn_result.fetchone()[0]
            
        return {
            "status": "connected",
            "database": current_db,
            "host": DB_HOST,
            "port": DB_PORT,
            "version": version,
            "active_connections": active_connections,
            "url": f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        }
        
    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 실패: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


class DatabaseManager:
    """
    데이터베이스 관리 클래스
    연결 풀 관리, 헬스체크, 백업 등의 기능 제공
    """
    
    def __init__(self):
        self.engine = engine
        self.session_local = SessionLocal
    
    def get_session(self) -> Session:
        """
        새로운 데이터베이스 세션 반환
        
        Returns:
            Session: 데이터베이스 세션
        """
        return self.session_local()
    
    def health_check(self) -> dict:
        """
        데이터베이스 헬스체크
        
        Returns:
            dict: 헬스체크 결과
        """
        try:
            start_time = time.time()
            
            with self.engine.connect() as connection:
                connection.execute("SELECT 1")
                
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_connection_info(self) -> dict:
        """
        연결 풀 정보 반환
        
        Returns:
            dict: 연결 풀 정보
        """
        pool = self.engine.pool
        
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
    
    def execute_raw_query(self, query: str, params: dict = None) -> list:
        """
        Raw SQL 쿼리 실행
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            
        Returns:
            list: 쿼리 결과
        """
        try:
            with self.engine.connect() as connection:
                if params:
                    result = connection.execute(query, params)
                else:
                    result = connection.execute(query)
                
                return [dict(row) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Raw 쿼리 실행 실패: {str(e)}")
            raise


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()