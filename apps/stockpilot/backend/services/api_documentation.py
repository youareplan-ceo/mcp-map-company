#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot API 문서 자동 생성 시스템
Swagger/OpenAPI 3.0 기반 종합 API 문서화
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import inspect
import ast

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """API 엔드포인트 정보"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]
    parameters: List[Dict]
    request_body: Optional[Dict]
    responses: Dict[str, Dict]
    security: List[Dict]

@dataclass
class APISchema:
    """API 스키마 정보"""
    name: str
    type: str
    properties: Dict[str, Any]
    required: List[str]
    example: Dict[str, Any]

class StockPilotAPIDocGenerator:
    """StockPilot API 문서 생성기"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or "/Users/youareplan/stockpilot-ai/docs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAPI 3.0 기본 구조
        self.openapi_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "StockPilot AI 투자 코파일럿 API",
                "description": "AI 기반 주식 투자 분석 및 의사결정 지원 시스템",
                "version": "1.0.0",
                "contact": {
                    "name": "StockPilot Team",
                    "email": "support@stockpilot.ai",
                    "url": "https://stockpilot.ai"
                },
                "license": {
                    "name": "MIT License",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "개발 서버"
                },
                {
                    "url": "https://api.stockpilot.ai",
                    "description": "프로덕션 서버"
                }
            ],
            "tags": [
                {"name": "주식분석", "description": "주식 데이터 분석 및 추천"},
                {"name": "포트폴리오", "description": "포트폴리오 관리 및 최적화"},
                {"name": "뉴스분석", "description": "금융 뉴스 분석 및 감정 분석"},
                {"name": "실시간데이터", "description": "실시간 시장 데이터 스트리밍"},
                {"name": "사용자관리", "description": "사용자 인증 및 권한 관리"},
                {"name": "비용관리", "description": "API 사용량 및 비용 관리"},
                {"name": "시스템모니터링", "description": "시스템 상태 및 헬스 체크"}
            ],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    },
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                },
                "schemas": {},
                "responses": {
                    "UnauthorizedError": {
                        "description": "인증 정보가 없거나 잘못됨",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Error"
                                }
                            }
                        }
                    },
                    "NotFoundError": {
                        "description": "요청한 리소스를 찾을 수 없음",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Error"
                                }
                            }
                        }
                    },
                    "ValidationError": {
                        "description": "입력 데이터 검증 실패",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationError"
                                }
                            }
                        }
                    }
                }
            }
        }
        
        self._add_common_schemas()
        self._add_api_endpoints()
    
    def _add_common_schemas(self):
        """공통 스키마 정의"""
        common_schemas = {
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "에러 메시지"
                    },
                    "code": {
                        "type": "string",
                        "description": "에러 코드"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "에러 발생 시간"
                    }
                },
                "required": ["error", "code"],
                "example": {
                    "error": "잘못된 요청입니다",
                    "code": "INVALID_REQUEST",
                    "timestamp": "2024-01-01T12:00:00Z"
                }
            },
            "ValidationError": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string"
                    },
                    "details": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                },
                "example": {
                    "error": "입력 데이터 검증 실패",
                    "details": [
                        {"field": "symbol", "message": "주식 심볼이 필요합니다"}
                    ]
                }
            },
            "StockData": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "주식 심볼 (예: AAPL, 005930)"
                    },
                    "name": {
                        "type": "string",
                        "description": "회사명"
                    },
                    "price": {
                        "type": "number",
                        "format": "float",
                        "description": "현재 주가"
                    },
                    "change": {
                        "type": "number",
                        "format": "float",
                        "description": "가격 변화"
                    },
                    "change_percent": {
                        "type": "number",
                        "format": "float",
                        "description": "가격 변화율 (%)"
                    },
                    "volume": {
                        "type": "integer",
                        "description": "거래량"
                    },
                    "market_cap": {
                        "type": "number",
                        "format": "float",
                        "description": "시가총액"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "데이터 수집 시간"
                    }
                },
                "required": ["symbol", "price"],
                "example": {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "price": 175.50,
                    "change": 2.50,
                    "change_percent": 1.45,
                    "volume": 45623000,
                    "market_cap": 2750000000000,
                    "timestamp": "2024-01-01T16:00:00Z"
                }
            },
            "StockAnalysis": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "recommendation": {
                        "type": "string",
                        "enum": ["강력매수", "매수", "보유", "매도", "강력매도"]
                    },
                    "target_price": {
                        "type": "number",
                        "format": "float"
                    },
                    "confidence": {
                        "type": "number",
                        "format": "float",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "factors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "impact": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        }
                    },
                    "risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "analysis_date": {
                        "type": "string",
                        "format": "date-time"
                    }
                },
                "example": {
                    "symbol": "AAPL",
                    "recommendation": "매수",
                    "target_price": 190.0,
                    "confidence": 0.85,
                    "factors": [
                        {
                            "category": "기술적 분석",
                            "impact": "긍정적",
                            "description": "상승 추세 지속"
                        }
                    ],
                    "risks": ["시장 변동성", "경쟁 심화"],
                    "analysis_date": "2024-01-01T12:00:00Z"
                }
            },
            "Portfolio": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "total_value": {"type": "number", "format": "float"},
                    "total_return": {"type": "number", "format": "float"},
                    "total_return_percent": {"type": "number", "format": "float"},
                    "positions": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/Position"
                        }
                    },
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                },
                "example": {
                    "id": "portfolio_123",
                    "name": "성장형 포트폴리오",
                    "total_value": 100000.0,
                    "total_return": 15000.0,
                    "total_return_percent": 15.0,
                    "positions": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T16:00:00Z"
                }
            },
            "Position": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "avg_cost": {"type": "number", "format": "float"},
                    "current_price": {"type": "number", "format": "float"},
                    "market_value": {"type": "number", "format": "float"},
                    "unrealized_pnl": {"type": "number", "format": "float"},
                    "unrealized_pnl_percent": {"type": "number", "format": "float"}
                },
                "example": {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "avg_cost": 150.0,
                    "current_price": 175.0,
                    "market_value": 17500.0,
                    "unrealized_pnl": 2500.0,
                    "unrealized_pnl_percent": 16.67
                }
            },
            "NewsArticle": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "content": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                    "published_at": {"type": "string", "format": "date-time"},
                    "source": {"type": "string"},
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"]
                    },
                    "sentiment_score": {
                        "type": "number",
                        "format": "float",
                        "minimum": -1,
                        "maximum": 1
                    },
                    "relevance": {
                        "type": "number",
                        "format": "float",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "example": {
                    "id": "news_123",
                    "title": "애플, 신제품 발표로 주가 상승",
                    "summary": "애플이 새로운 아이폰을 발표하며 시장의 긍정적 반응을 얻고 있다",
                    "url": "https://example.com/news/123",
                    "published_at": "2024-01-01T12:00:00Z",
                    "source": "Reuters",
                    "sentiment": "positive",
                    "sentiment_score": 0.75,
                    "relevance": 0.95,
                    "symbols": ["AAPL"]
                }
            }
        }
        
        self.openapi_spec["components"]["schemas"].update(common_schemas)
    
    def _add_api_endpoints(self):
        """API 엔드포인트 정의"""
        endpoints = {
            # 주식 분석 API
            "/api/v1/stocks/{symbol}/data": {
                "get": {
                    "tags": ["주식분석"],
                    "summary": "주식 데이터 조회",
                    "description": "지정된 주식의 실시간 데이터를 조회합니다",
                    "parameters": [
                        {
                            "name": "symbol",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "주식 심볼 (예: AAPL, 005930)",
                            "example": "AAPL"
                        },
                        {
                            "name": "interval",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["1m", "5m", "15m", "30m", "1h", "1d"],
                                "default": "1d"
                            },
                            "description": "데이터 간격"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "성공적으로 데이터 조회",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StockData"}
                                }
                            }
                        },
                        "404": {"$ref": "#/components/responses/NotFoundError"}
                    },
                    "security": [{"ApiKeyAuth": []}]
                }
            },
            "/api/v1/stocks/{symbol}/analysis": {
                "get": {
                    "tags": ["주식분석"],
                    "summary": "주식 분석 결과 조회",
                    "description": "AI 기반 주식 분석 및 투자 추천을 제공합니다",
                    "parameters": [
                        {
                            "name": "symbol",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "주식 심볼",
                            "example": "AAPL"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "분석 결과",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StockAnalysis"}
                                }
                            }
                        }
                    },
                    "security": [{"BearerAuth": []}]
                }
            },
            "/api/v1/portfolio": {
                "get": {
                    "tags": ["포트폴리오"],
                    "summary": "포트폴리오 목록 조회",
                    "description": "사용자의 포트폴리오 목록을 조회합니다",
                    "responses": {
                        "200": {
                            "description": "포트폴리오 목록",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Portfolio"}
                                    }
                                }
                            }
                        }
                    },
                    "security": [{"BearerAuth": []}]
                },
                "post": {
                    "tags": ["포트폴리오"],
                    "summary": "새 포트폴리오 생성",
                    "description": "새로운 포트폴리오를 생성합니다",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "investment_style": {
                                            "type": "string",
                                            "enum": ["aggressive", "balanced", "conservative"]
                                        }
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "포트폴리오 생성 성공",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Portfolio"}
                                }
                            }
                        }
                    },
                    "security": [{"BearerAuth": []}]
                }
            },
            "/api/v1/news": {
                "get": {
                    "tags": ["뉴스분석"],
                    "summary": "금융 뉴스 조회",
                    "description": "최신 금융 뉴스를 감정 분석과 함께 제공합니다",
                    "parameters": [
                        {
                            "name": "symbol",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "특정 주식 심볼 관련 뉴스"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 20, "maximum": 100},
                            "description": "조회할 뉴스 개수"
                        },
                        {
                            "name": "sentiment",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["positive", "neutral", "negative"]
                            },
                            "description": "감정 필터링"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "뉴스 목록",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "articles": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/NewsArticle"}
                                            },
                                            "total_count": {"type": "integer"},
                                            "has_more": {"type": "boolean"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/realtime/subscribe": {
                "post": {
                    "tags": ["실시간데이터"],
                    "summary": "실시간 데이터 구독",
                    "description": "WebSocket을 통한 실시간 데이터 스트림 구독",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "symbols": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "data_types": {
                                            "type": "array",
                                            "items": {
                                                "type": "string",
                                                "enum": ["price", "volume", "news", "analysis"]
                                            }
                                        }
                                    },
                                    "required": ["symbols"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "구독 성공",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "subscription_id": {"type": "string"},
                                            "websocket_url": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "security": [{"BearerAuth": []}]
                }
            },
            "/api/v1/system/health": {
                "get": {
                    "tags": ["시스템모니터링"],
                    "summary": "시스템 헬스 체크",
                    "description": "시스템의 전반적인 상태를 확인합니다",
                    "responses": {
                        "200": {
                            "description": "시스템 상태",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["healthy", "degraded", "unhealthy"]
                                            },
                                            "timestamp": {"type": "string", "format": "date-time"},
                                            "services": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "object",
                                                    "properties": {
                                                        "status": {"type": "string"},
                                                        "response_time": {"type": "number"},
                                                        "last_check": {"type": "string", "format": "date-time"}
                                                    }
                                                }
                                            },
                                            "version": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/usage/stats": {
                "get": {
                    "tags": ["비용관리"],
                    "summary": "API 사용 통계",
                    "description": "API 사용량 및 비용 정보를 제공합니다",
                    "parameters": [
                        {
                            "name": "period",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["today", "week", "month"],
                                "default": "today"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "사용 통계",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "period": {"type": "string"},
                                            "total_requests": {"type": "integer"},
                                            "total_cost": {"type": "number", "format": "float"},
                                            "by_endpoint": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "object",
                                                    "properties": {
                                                        "requests": {"type": "integer"},
                                                        "cost": {"type": "number"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "security": [{"BearerAuth": []}]
                }
            }
        }
        
        self.openapi_spec["paths"].update(endpoints)
    
    def generate_openapi_json(self) -> str:
        """OpenAPI JSON 문서 생성"""
        json_path = self.output_dir / "openapi.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.openapi_spec, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OpenAPI JSON 문서 생성: {json_path}")
        return str(json_path)
    
    def generate_openapi_yaml(self) -> str:
        """OpenAPI YAML 문서 생성"""
        yaml_path = self.output_dir / "openapi.yaml"
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.openapi_spec, f, default_flow_style=False, 
                     allow_unicode=True, sort_keys=False)
        
        logger.info(f"OpenAPI YAML 문서 생성: {yaml_path}")
        return str(yaml_path)
    
    def generate_swagger_html(self) -> str:
        """Swagger UI HTML 생성"""
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>StockPilot API 문서</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
    <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.9.0/favicon-32x32.png" sizes="32x32" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        
        body {{
            margin: 0;
            background: #fafafa;
            font-family: 'Noto Sans KR', sans-serif;
        }}
        
        .swagger-ui .topbar {{
            background-color: #2c3e50;
        }}
        
        .swagger-ui .topbar .download-url-wrapper input[type=text] {{
            border: 2px solid #34495e;
        }}
        
        .custom-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }}
        
        .custom-header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .custom-header p {{
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }}
    </style>
</head>

<body>
    <div class="custom-header">
        <h1>📊 StockPilot API</h1>
        <p>AI 기반 주식 투자 분석 및 의사결정 지원 시스템</p>
    </div>
    
    <div id="swagger-ui"></div>

    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: './openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 2,
                defaultModelExpandDepth: 2,
                docExpansion: 'list',
                operationsSorter: 'alpha',
                tagsSorter: 'alpha',
                filter: true,
                tryItOutEnabled: true,
                requestInterceptor: function(request) {{
                    // API 키 또는 인증 토큰을 자동으로 추가
                    if (localStorage.getItem('stockpilot_api_key')) {{
                        request.headers['X-API-Key'] = localStorage.getItem('stockpilot_api_key');
                    }}
                    return request;
                }},
                responseInterceptor: function(response) {{
                    // 응답 처리 로직
                    return response;
                }}
            }});
        }};
    </script>
</body>
</html>
        """
        
        html_path = self.output_dir / "swagger-ui.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Swagger UI HTML 생성: {html_path}")
        return str(html_path)
    
    def generate_postman_collection(self) -> str:
        """Postman Collection 생성"""
        postman_collection = {
            "info": {
                "name": "StockPilot API",
                "description": "AI 기반 주식 투자 분석 시스템 API 컬렉션",
                "version": "1.0.0",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:8000",
                    "type": "string"
                },
                {
                    "key": "api_key",
                    "value": "your_api_key_here",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # API 엔드포인트를 Postman 요청으로 변환
        for path, methods in self.openapi_spec["paths"].items():
            folder = {
                "name": path,
                "item": []
            }
            
            for method, spec in methods.items():
                request = {
                    "name": spec.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "url": {
                            "raw": "{{base_url}}" + path,
                            "host": ["{{base_url}}"],
                            "path": path.split("/")[1:]
                        }
                    },
                    "response": []
                }
                
                # 쿼리 파라미터 추가
                if "parameters" in spec:
                    query_params = []
                    for param in spec["parameters"]:
                        if param["in"] == "query":
                            query_params.append({
                                "key": param["name"],
                                "value": param.get("example", ""),
                                "description": param.get("description", "")
                            })
                    
                    if query_params:
                        request["request"]["url"]["query"] = query_params
                
                # 요청 본문 추가
                if "requestBody" in spec:
                    request["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps({}, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
                
                folder["item"].append(request)
            
            postman_collection["item"].append(folder)
        
        collection_path = self.output_dir / "postman_collection.json"
        
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(postman_collection, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Postman Collection 생성: {collection_path}")
        return str(collection_path)
    
    def generate_api_client_examples(self) -> str:
        """API 클라이언트 예제 생성"""
        examples = {
            "python": {
                "description": "Python 클라이언트 예제",
                "code": '''
import requests
import json

class StockPilotClient:
    def __init__(self, api_key, base_url="http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_stock_data(self, symbol, interval="1d"):
        """주식 데이터 조회"""
        url = f"{self.base_url}/api/v1/stocks/{symbol}/data"
        params = {"interval": interval}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_stock_analysis(self, symbol):
        """주식 분석 결과 조회"""
        url = f"{self.base_url}/api/v1/stocks/{symbol}/analysis"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_news(self, symbol=None, limit=20):
        """금융 뉴스 조회"""
        url = f"{self.base_url}/api/v1/news"
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

# 사용 예제
client = StockPilotClient("your_api_key_here")

# 애플 주식 데이터 조회
stock_data = client.get_stock_data("AAPL")
print(f"AAPL 현재가: ${stock_data['price']}")

# 주식 분석 결과
analysis = client.get_stock_analysis("AAPL")
print(f"투자 추천: {analysis['recommendation']}")

# 최신 뉴스
news = client.get_news("AAPL", limit=5)
for article in news['articles']:
    print(f"- {article['title']} (감정: {article['sentiment']})")
                '''
            },
            "javascript": {
                "description": "JavaScript/Node.js 클라이언트 예제",
                "code": '''
class StockPilotClient {
    constructor(apiKey, baseUrl = "http://localhost:8000") {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            "X-API-Key": apiKey,
            "Content-Type": "application/json"
        };
    }
    
    async getStockData(symbol, interval = "1d") {
        const url = `${this.baseUrl}/api/v1/stocks/${symbol}/data?interval=${interval}`;
        const response = await fetch(url, { headers: this.headers });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async getStockAnalysis(symbol) {
        const url = `${this.baseUrl}/api/v1/stocks/${symbol}/analysis`;
        const response = await fetch(url, { headers: this.headers });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async getNews(symbol = null, limit = 20) {
        let url = `${this.baseUrl}/api/v1/news?limit=${limit}`;
        if (symbol) {
            url += `&symbol=${symbol}`;
        }
        
        const response = await fetch(url, { headers: this.headers });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
}

// 사용 예제
const client = new StockPilotClient("your_api_key_here");

// 애플 주식 데이터 조회
client.getStockData("AAPL")
    .then(data => console.log(`AAPL 현재가: $${data.price}`))
    .catch(error => console.error("에러:", error));

// 주식 분석 결과
client.getStockAnalysis("AAPL")
    .then(analysis => console.log(`투자 추천: ${analysis.recommendation}`))
    .catch(error => console.error("에러:", error));
                '''
            },
            "curl": {
                "description": "cURL 명령어 예제",
                "code": '''
#!/bin/bash

# API 키 설정
API_KEY="your_api_key_here"
BASE_URL="http://localhost:8000"

# 주식 데이터 조회
curl -X GET "$BASE_URL/api/v1/stocks/AAPL/data?interval=1d" \\
    -H "X-API-Key: $API_KEY" \\
    -H "Content-Type: application/json"

# 주식 분석 결과 조회
curl -X GET "$BASE_URL/api/v1/stocks/AAPL/analysis" \\
    -H "Authorization: Bearer $JWT_TOKEN" \\
    -H "Content-Type: application/json"

# 금융 뉴스 조회
curl -X GET "$BASE_URL/api/v1/news?symbol=AAPL&limit=5" \\
    -H "X-API-Key: $API_KEY" \\
    -H "Content-Type: application/json"

# 새 포트폴리오 생성
curl -X POST "$BASE_URL/api/v1/portfolio" \\
    -H "Authorization: Bearer $JWT_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{
        "name": "성장형 포트폴리오",
        "description": "기술주 중심의 성장형 투자",
        "investment_style": "aggressive"
    }'

# 시스템 헬스 체크
curl -X GET "$BASE_URL/api/v1/system/health"
                '''
            }
        }
        
        examples_path = self.output_dir / "api_client_examples.json"
        
        with open(examples_path, 'w', encoding='utf-8') as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)
        
        logger.info(f"API 클라이언트 예제 생성: {examples_path}")
        return str(examples_path)
    
    def generate_all_docs(self) -> Dict[str, str]:
        """모든 API 문서 생성"""
        logger.info("StockPilot API 문서 생성 시작")
        
        generated_files = {}
        
        # OpenAPI 문서
        generated_files["openapi_json"] = self.generate_openapi_json()
        generated_files["openapi_yaml"] = self.generate_openapi_yaml()
        
        # Swagger UI
        generated_files["swagger_html"] = self.generate_swagger_html()
        
        # Postman Collection
        generated_files["postman_collection"] = self.generate_postman_collection()
        
        # API 클라이언트 예제
        generated_files["client_examples"] = self.generate_api_client_examples()
        
        logger.info("모든 API 문서 생성 완료")
        return generated_files

def main():
    """메인 실행 함수"""
    try:
        generator = StockPilotAPIDocGenerator()
        files = generator.generate_all_docs()
        
        print("\n" + "="*60)
        print("StockPilot API 문서 생성 완료")
        print("="*60)
        
        for doc_type, file_path in files.items():
            print(f"✓ {doc_type}: {file_path}")
        
        print(f"\n📖 문서 확인 방법:")
        print(f"  - Swagger UI: swagger-ui.html 파일을 브라우저로 열기")
        print(f"  - Postman: postman_collection.json을 Postman에 임포트")
        print(f"  - 개발자: api_client_examples.json 참고")
        
    except Exception as e:
        logger.error(f"문서 생성 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main()