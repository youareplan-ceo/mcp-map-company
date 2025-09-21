#!/usr/bin/env python3
"""
에러 유형별 런북 템플릿 모듈 (Error Type Runbook Templates Module)
=================================================================

목적: 에러 유형별 "사람이 보는" 런북 템플릿 제공
Purpose: Provide human-readable runbook templates for different error types

기능:
- CI/CD 에러 코드별 상세 런북 제공
- 원인 분석, 체크리스트, 수동 조치 가이드
- Markdown 형식 렌더링 지원
- 한국어 템플릿 및 주석 포함

작성자: CI/CD 자동화 팀
버전: 1.0.0
최종 수정: 2025-09-21
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# 런북 템플릿 데이터베이스
RUNBOOK_TEMPLATES = {
    "dependency_install_failed": {
        "title": "🔧 의존성 설치 실패",
        "severity": "HIGH",
        "category": "BUILD",
        "estimated_resolution_time": "15-30분",
        "description": "패키지 의존성 설치 중 오류가 발생했습니다. 네트워크 문제, 저장소 접근 권한, 또는 패키지 버전 충돌이 원인일 수 있습니다.",
        "common_causes": [
            "네트워크 연결 불안정 또는 차단",
            "패키지 저장소 서버 다운타임",
            "인증 정보 만료 또는 권한 부족",
            "패키지 버전 충돌 또는 호환성 문제",
            "로컬 캐시 손상",
            "디스크 공간 부족"
        ],
        "checklist": [
            "📡 네트워크 연결 상태 확인",
            "🔐 저장소 인증 정보 검증",
            "📦 패키지 매니저 캐시 상태 확인",
            "💾 디스크 공간 확인 (최소 1GB 여유 공간)",
            "🔒 방화벽 및 프록시 설정 확인",
            "📋 패키지 의존성 트리 분석",
            "🏷️ 패키지 버전 태그 및 가용성 확인"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "캐시 정리",
                "commands": [
                    "npm cache clean --force  # Node.js",
                    "pip cache purge  # Python",
                    "mvn dependency:purge-local-repository  # Maven"
                ],
                "description": "손상된 캐시를 정리하여 새로운 다운로드를 시도합니다."
            },
            {
                "step": 2,
                "title": "의존성 파일 검증",
                "commands": [
                    "npm audit fix  # Node.js 취약점 수정",
                    "pip check  # Python 의존성 충돌 확인",
                    "mvn dependency:tree  # Maven 의존성 트리 확인"
                ],
                "description": "의존성 파일의 무결성과 버전 호환성을 확인합니다."
            },
            {
                "step": 3,
                "title": "수동 재시도",
                "commands": [
                    "rm -rf node_modules && npm install  # Node.js 완전 재설치",
                    "pip install --force-reinstall -r requirements.txt  # Python 강제 재설치",
                    "mvn clean install -U  # Maven 강제 업데이트"
                ],
                "description": "의존성을 완전히 삭제 후 재설치합니다."
            }
        ],
        "prevention_tips": [
            "정기적인 의존성 업데이트 및 보안 패치",
            "의존성 잠금 파일 사용 (package-lock.json, requirements.txt)",
            "사내 패키지 미러 구축 고려",
            "CI 캐시 정책 최적화"
        ],
        "related_links": [
            "https://docs.npmjs.com/cli/v8/commands/npm-install",
            "https://pip.pypa.io/en/stable/user_guide/",
            "https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html"
        ]
    },

    "test_timeout": {
        "title": "⏰ 테스트 실행 시간 초과",
        "severity": "MEDIUM",
        "category": "TEST",
        "estimated_resolution_time": "10-20분",
        "description": "테스트 실행이 설정된 시간 제한을 초과했습니다. 느린 테스트, 무한 루프, 또는 외부 서비스 의존성이 원인일 수 있습니다.",
        "common_causes": [
            "외부 API 또는 데이터베이스 응답 지연",
            "테스트 코드 내 무한 루프 또는 데드락",
            "테스트 환경 리소스 부족",
            "네트워크 I/O 대기 시간 증가",
            "테스트 데이터 크기 문제",
            "Mock 설정 누락으로 인한 실제 외부 호출"
        ],
        "checklist": [
            "🕐 개별 테스트 실행 시간 분석",
            "🔍 로그에서 느린 테스트 케이스 식별",
            "🌐 외부 서비스 의존성 확인",
            "💾 테스트 환경 리소스 상태 점검",
            "🔄 테스트 격리 상태 확인",
            "📊 테스트 데이터 크기 검토",
            "🎭 Mock/Stub 설정 검증"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "느린 테스트 식별",
                "commands": [
                    "pytest --durations=10  # Python: 가장 느린 10개 테스트",
                    "jest --verbose  # JavaScript: 상세 실행 시간",
                    "mvn test -Dtest.timeout=30000  # Java: 타임아웃 설정"
                ],
                "description": "가장 시간이 오래 걸리는 테스트를 식별합니다."
            },
            {
                "step": 2,
                "title": "타임아웃 임시 증가",
                "commands": [
                    "pytest --timeout=300  # Python: 5분으로 증가",
                    "jest --testTimeout=300000  # Jest: 5분으로 증가",
                    "export MAVEN_OPTS='-Dtest.timeout=300000'  # Maven"
                ],
                "description": "임시로 타임아웃을 늘려 실행 가능한지 확인합니다."
            },
            {
                "step": 3,
                "title": "테스트 최적화",
                "commands": [
                    "# 외부 의존성 Mock 처리",
                    "# 테스트 데이터 크기 최소화",
                    "# 병렬 실행 설정 조정",
                    "pytest -n auto  # 병렬 실행 (pytest-xdist)"
                ],
                "description": "테스트 성능을 개선하여 실행 시간을 단축합니다."
            }
        ],
        "prevention_tips": [
            "외부 의존성에 대한 철저한 Mock 사용",
            "테스트별 적절한 타임아웃 설정",
            "통합 테스트와 단위 테스트 분리",
            "테스트 데이터 최소화 및 팩토리 패턴 활용"
        ],
        "related_links": [
            "https://docs.pytest.org/en/stable/how-to/timeout.html",
            "https://jestjs.io/docs/configuration#testtimeout-number",
            "https://maven.apache.org/surefire/maven-surefire-plugin/test-mojo.html#timeout"
        ]
    },

    "build_timeout": {
        "title": "🏗️ 빌드 시간 초과",
        "severity": "HIGH",
        "category": "BUILD",
        "estimated_resolution_time": "20-45분",
        "description": "빌드 프로세스가 설정된 시간 제한을 초과했습니다. 컴파일 시간 증가, 리소스 부족, 또는 빌드 설정 문제가 원인일 수 있습니다.",
        "common_causes": [
            "소스 코드 크기 증가로 인한 컴파일 시간 연장",
            "빌드 머신 리소스 부족 (CPU/메모리)",
            "의존성 다운로드 시간 증가",
            "빌드 캐시 미사용 또는 캐시 무효화",
            "빌드 도구 비효율적 설정",
            "병렬 빌드 설정 부족"
        ],
        "checklist": [
            "⚡ 빌드 머신 리소스 사용률 확인",
            "📦 의존성 다운로드 시간 분석",
            "🗂️ 빌드 캐시 상태 및 활용도 점검",
            "🔧 빌드 설정 파일 검토",
            "📊 이전 빌드와 시간 비교 분석",
            "🎯 빌드 단계별 시간 측정",
            "🏃 병렬 처리 설정 확인"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "빌드 캐시 활성화",
                "commands": [
                    "# Docker 멀티스테이지 빌드 캐시",
                    "docker build --cache-from=previous-image .",
                    "# Maven 로컬 저장소 캐시",
                    "mvn clean install -Dmaven.repo.local=/cache/maven",
                    "# Gradle 빌드 캐시",
                    "./gradlew build --build-cache"
                ],
                "description": "빌드 캐시를 활성화하여 중복 작업을 최소화합니다."
            },
            {
                "step": 2,
                "title": "병렬 빌드 설정",
                "commands": [
                    "make -j$(nproc)  # Make 병렬 빌드",
                    "mvn -T 1C clean install  # Maven 병렬 빌드",
                    "./gradlew build --parallel  # Gradle 병렬 빌드",
                    "npm run build -- --max-old-space-size=4096  # Node.js 메모리 증가"
                ],
                "description": "사용 가능한 CPU 코어를 활용하여 병렬 빌드를 수행합니다."
            },
            {
                "step": 3,
                "title": "빌드 최적화",
                "commands": [
                    "# 불필요한 파일 제외 (.dockerignore, .gitignore)",
                    "# 증분 빌드 활용",
                    "# 빌드 아티팩트 분할",
                    "# 조건부 빌드 스텝 구성"
                ],
                "description": "빌드 프로세스를 최적화하여 전체 시간을 단축합니다."
            }
        ],
        "prevention_tips": [
            "CI/CD 파이프라인에서 적극적인 캐시 활용",
            "빌드 머신 리소스 모니터링 및 스케일링",
            "불필요한 빌드 단계 제거",
            "증분 빌드 및 변경 감지 활용"
        ],
        "related_links": [
            "https://docs.docker.com/build/cache/",
            "https://maven.apache.org/guides/mini/guide-building-for-different-environments.html",
            "https://docs.gradle.org/current/userguide/build_cache.html"
        ]
    },

    "network_error": {
        "title": "🌐 네트워크 연결 오류",
        "severity": "MEDIUM",
        "category": "INFRASTRUCTURE",
        "estimated_resolution_time": "5-15분",
        "description": "네트워크 연결 문제로 인해 외부 리소스 접근이 실패했습니다. DNS 해석, 방화벽, 또는 서비스 다운타임이 원인일 수 있습니다.",
        "common_causes": [
            "DNS 해석 실패",
            "방화벽 또는 보안 그룹 규칙 차단",
            "외부 서비스 일시적 다운타임",
            "프록시 설정 문제",
            "SSL/TLS 인증서 문제",
            "네트워크 라우팅 문제"
        ],
        "checklist": [
            "🔍 DNS 해석 상태 확인",
            "🔥 방화벽 규칙 검토",
            "🌍 외부 서비스 상태 페이지 확인",
            "🔐 SSL 인증서 유효성 검사",
            "🛡️ 프록시 설정 검증",
            "📡 네트워크 연결성 테스트",
            "⏰ 타임아웃 설정 검토"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "네트워크 연결 진단",
                "commands": [
                    "nslookup google.com  # DNS 해석 테스트",
                    "ping -c 4 8.8.8.8  # 기본 연결 테스트",
                    "curl -I https://httpbin.org/status/200  # HTTP 연결 테스트",
                    "telnet smtp.gmail.com 587  # 포트 연결 테스트"
                ],
                "description": "기본적인 네트워크 연결 상태를 진단합니다."
            },
            {
                "step": 2,
                "title": "외부 서비스 상태 확인",
                "commands": [
                    "curl -s https://status.github.com/api/status.json",
                    "curl -s https://status.npmjs.org/api/v2/status.json",
                    "# 사용하는 외부 서비스의 상태 페이지 확인"
                ],
                "description": "의존하는 외부 서비스의 현재 상태를 확인합니다."
            },
            {
                "step": 3,
                "title": "재시도 및 대안 설정",
                "commands": [
                    "# HTTP 클라이언트 재시도 설정",
                    "curl --retry 3 --retry-delay 5 URL",
                    "# 대안 미러 서버 사용",
                    "npm config set registry https://registry.npm.taobao.org/",
                    "# 타임아웃 증가",
                    "curl --connect-timeout 30 --max-time 300 URL"
                ],
                "description": "재시도 로직을 적용하거나 대안 서버를 사용합니다."
            }
        ],
        "prevention_tips": [
            "네트워크 요청에 적절한 재시도 로직 구현",
            "외부 의존성 최소화 및 대안 서버 준비",
            "네트워크 모니터링 및 알림 설정",
            "오프라인 작업 모드 지원 고려"
        ],
        "related_links": [
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
            "https://curl.se/docs/manpage.html",
            "https://docs.docker.com/network/troubleshooting/"
        ]
    },

    "cache_corruption": {
        "title": "🗂️ 캐시 손상",
        "severity": "MEDIUM",
        "category": "BUILD",
        "estimated_resolution_time": "10-25분",
        "description": "빌드 또는 의존성 캐시가 손상되어 예상치 못한 오류가 발생했습니다. 캐시 정리 및 재구성이 필요합니다.",
        "common_causes": [
            "불완전한 다운로드로 인한 캐시 파일 손상",
            "디스크 공간 부족으로 인한 부분 쓰기",
            "동시 접근으로 인한 캐시 충돌",
            "캐시 메타데이터 불일치",
            "파일 시스템 오류",
            "캐시 만료 정책 문제"
        ],
        "checklist": [
            "💾 디스크 공간 사용률 확인",
            "🔍 캐시 디렉토리 무결성 검사",
            "📁 캐시 파일 권한 확인",
            "🔄 캐시 메타데이터 일관성 검증",
            "⚡ 동시 접근 충돌 가능성 분석",
            "📊 캐시 히트율 및 성능 분석",
            "🧹 캐시 정리 정책 검토"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "캐시 무결성 검사",
                "commands": [
                    "npm cache verify  # npm 캐시 검증",
                    "pip cache info  # pip 캐시 정보 확인",
                    "docker system df  # Docker 캐시 사용량",
                    "gradle cleanBuildCache  # Gradle 캐시 정리"
                ],
                "description": "현재 캐시 상태를 검사하고 문제를 식별합니다."
            },
            {
                "step": 2,
                "title": "손상된 캐시 정리",
                "commands": [
                    "npm cache clean --force  # npm 캐시 강제 정리",
                    "pip cache purge  # pip 캐시 완전 삭제",
                    "docker system prune -af  # Docker 캐시 정리",
                    "rm -rf ~/.gradle/caches/  # Gradle 캐시 수동 삭제"
                ],
                "description": "손상된 캐시를 완전히 제거합니다."
            },
            {
                "step": 3,
                "title": "캐시 재구성",
                "commands": [
                    "npm install  # npm 의존성 재설치",
                    "pip install --force-reinstall -r requirements.txt",
                    "docker build --no-cache .  # Docker 이미지 캐시 없이 빌드",
                    "./gradlew build --refresh-dependencies  # Gradle 의존성 갱신"
                ],
                "description": "깨끗한 상태에서 캐시를 재구성합니다."
            }
        ],
        "prevention_tips": [
            "정기적인 캐시 정리 스케줄 설정",
            "충분한 디스크 공간 확보",
            "캐시 잠금 메커니즘 구현",
            "캐시 백업 및 복구 전략 수립"
        ],
        "related_links": [
            "https://docs.npmjs.com/cli/v8/commands/npm-cache",
            "https://pip.pypa.io/en/stable/cli/pip_cache/",
            "https://docs.docker.com/config/pruning/"
        ]
    },

    "worker_unavailable": {
        "title": "👷 워커 사용 불가",
        "severity": "HIGH",
        "category": "INFRASTRUCTURE",
        "estimated_resolution_time": "15-30분",
        "description": "CI 워커가 응답하지 않거나 사용할 수 없는 상태입니다. 리소스 부족, 프로세스 크래시, 또는 네트워크 문제가 원인일 수 있습니다.",
        "common_causes": [
            "워커 프로세스 크래시 또는 데드락",
            "메모리 부족 (OOM) 상황",
            "CPU 과부하 상태",
            "디스크 공간 부족",
            "네트워크 연결 끊김",
            "워커 등록 정보 만료"
        ],
        "checklist": [
            "🔍 워커 프로세스 상태 확인",
            "💾 시스템 리소스 사용률 점검",
            "📡 네트워크 연결 상태 검증",
            "📋 워커 등록 정보 확인",
            "📊 워커 로그 분석",
            "🔄 워커 풀 상태 점검",
            "⚡ 작업 큐 상태 확인"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "워커 상태 진단",
                "commands": [
                    "ps aux | grep worker  # 워커 프로세스 확인",
                    "systemctl status gitlab-runner  # GitLab Runner 상태",
                    "docker ps | grep runner  # Docker 러너 상태",
                    "kubectl get pods -l app=ci-worker  # K8s 워커 상태"
                ],
                "description": "현재 워커의 실행 상태를 확인합니다."
            },
            {
                "step": 2,
                "title": "리소스 사용률 확인",
                "commands": [
                    "top -p $(pgrep worker)  # 워커 프로세스 리소스 사용률",
                    "df -h  # 디스크 공간 확인",
                    "free -h  # 메모리 사용률 확인",
                    "iostat -x 1 5  # I/O 상태 모니터링"
                ],
                "description": "시스템 리소스 상태를 점검합니다."
            },
            {
                "step": 3,
                "title": "워커 재시작",
                "commands": [
                    "systemctl restart gitlab-runner  # GitLab Runner 재시작",
                    "docker restart runner-container  # Docker 워커 재시작",
                    "kubectl rollout restart deployment/ci-worker  # K8s 워커 재시작",
                    "./config.sh remove && ./config.sh --url ...  # 워커 재등록"
                ],
                "description": "워커를 재시작하여 정상 상태로 복구합니다."
            }
        ],
        "prevention_tips": [
            "워커 리소스 모니터링 및 알림 설정",
            "자동 재시작 및 헬스체크 구현",
            "워커 풀 크기 동적 조정",
            "정기적인 워커 재시작 스케줄"
        ],
        "related_links": [
            "https://docs.gitlab.com/runner/",
            "https://docs.github.com/en/actions/hosting-your-own-runners",
            "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"
        ]
    },

    "flaky_test": {
        "title": "🎭 플래키 테스트",
        "severity": "MEDIUM",
        "category": "TEST",
        "estimated_resolution_time": "30-60분",
        "description": "간헐적으로 성공/실패하는 불안정한 테스트입니다. 타이밍 문제, 외부 의존성, 또는 테스트 격리 부족이 원인일 수 있습니다.",
        "common_causes": [
            "비동기 작업 타이밍 문제",
            "외부 서비스 의존성",
            "테스트 간 상태 공유 및 격리 부족",
            "랜덤 데이터 사용",
            "시간 의존적 로직",
            "리소스 경합 상황"
        ],
        "checklist": [
            "🔄 테스트 반복 실행으로 재현율 확인",
            "📊 실패 패턴 및 환경 분석",
            "🎯 외부 의존성 식별",
            "⏰ 타이밍 관련 코드 검토",
            "🔒 테스트 격리 상태 확인",
            "📋 테스트 데이터 의존성 분석",
            "🌐 환경별 실행 결과 비교"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "플래키 테스트 재현",
                "commands": [
                    "pytest test_flaky.py --count=10  # 10회 반복 실행",
                    "npm test -- --testNamePattern='flaky' --runInBand  # 순차 실행",
                    "for i in {1..20}; do npm test && echo \"Pass $i\" || echo \"Fail $i\"; done"
                ],
                "description": "테스트를 반복 실행하여 실패 패턴을 파악합니다."
            },
            {
                "step": 2,
                "title": "외부 의존성 Mock 처리",
                "commands": [
                    "# API 호출 Mock 설정",
                    "# 시간 의존성 제거 (freezegun, timecop)",
                    "# 랜덤 시드 고정",
                    "# 데이터베이스 트랜잭션 롤백"
                ],
                "description": "외부 요인을 제거하여 테스트를 안정화합니다."
            },
            {
                "step": 3,
                "title": "테스트 격리 강화",
                "commands": [
                    "# 테스트별 독립 환경 설정",
                    "# setUp/tearDown 메서드 강화",
                    "# 전역 상태 초기화",
                    "# 병렬 실행 비활성화 (필요시)"
                ],
                "description": "테스트 간 간섭을 최소화하여 격리를 강화합니다."
            }
        ],
        "prevention_tips": [
            "철저한 테스트 격리 및 독립성 확보",
            "외부 의존성에 대한 Mock/Stub 활용",
            "시간 의존적 로직 최소화",
            "플래키 테스트 모니터링 및 추적 시스템 구축"
        ],
        "related_links": [
            "https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html",
            "https://martinfowler.com/articles/nonDeterminism.html",
            "https://docs.pytest.org/en/stable/how-to/flaky.html"
        ]
    },

    "disk_space_full": {
        "title": "💾 디스크 공간 부족",
        "severity": "HIGH",
        "category": "INFRASTRUCTURE",
        "estimated_resolution_time": "10-20분",
        "description": "빌드 머신의 디스크 공간이 부족하여 작업을 계속할 수 없습니다. 로그 파일, 캐시, 또는 임시 파일 정리가 필요합니다.",
        "common_causes": [
            "빌드 아티팩트 누적",
            "로그 파일 과다 생성",
            "캐시 파일 무제한 증가",
            "임시 파일 정리 실패",
            "Docker 이미지 및 컨테이너 누적",
            "의존성 파일 중복 저장"
        ],
        "checklist": [
            "💾 전체 디스크 사용률 확인",
            "📁 대용량 디렉토리 식별",
            "🗂️ 캐시 및 임시 파일 크기 점검",
            "📊 로그 파일 크기 및 로테이션 상태",
            "🐳 Docker 리소스 사용률 확인",
            "🧹 정리 가능한 파일 목록 작성",
            "📈 디스크 사용 증가 패턴 분석"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "디스크 사용량 분석",
                "commands": [
                    "df -h  # 파일시스템별 사용률",
                    "du -sh /* 2>/dev/null | sort -hr  # 디렉토리별 크기",
                    "find / -type f -size +100M 2>/dev/null  # 100MB 이상 파일",
                    "docker system df  # Docker 디스크 사용량"
                ],
                "description": "디스크 공간을 많이 사용하는 위치를 파악합니다."
            },
            {
                "step": 2,
                "title": "즉시 정리 작업",
                "commands": [
                    "docker system prune -af  # Docker 정리",
                    "npm cache clean --force  # npm 캐시 정리",
                    "pip cache purge  # pip 캐시 정리",
                    "rm -rf /tmp/* /var/tmp/*  # 임시 파일 정리",
                    "journalctl --vacuum-time=7d  # 시스템 로그 정리"
                ],
                "description": "안전하게 제거 가능한 파일들을 정리합니다."
            },
            {
                "step": 3,
                "title": "로그 로테이션 설정",
                "commands": [
                    "logrotate -f /etc/logrotate.conf  # 로그 로테이션 강제 실행",
                    "# 로그 크기 제한 설정",
                    "# 오래된 빌드 아티팩트 자동 삭제 스크립트",
                    "# 캐시 크기 제한 설정"
                ],
                "description": "향후 디스크 공간 부족을 방지하는 설정을 적용합니다."
            }
        ],
        "prevention_tips": [
            "자동 로그 로테이션 및 정리 정책 설정",
            "빌드 아티팩트 보관 기간 제한",
            "디스크 사용량 모니터링 및 알림",
            "정기적인 정리 스크립트 스케줄링"
        ],
        "related_links": [
            "https://docs.docker.com/config/pruning/",
            "https://www.freedesktop.org/software/systemd/man/journalctl.html",
            "https://linux.die.net/man/8/logrotate"
        ]
    },

    "memory_limit": {
        "title": "🧠 메모리 한계 초과",
        "severity": "HIGH",
        "category": "INFRASTRUCTURE",
        "estimated_resolution_time": "15-30분",
        "description": "빌드 프로세스가 할당된 메모리 한계를 초과했습니다. 메모리 사용량 최적화 또는 리소스 한계 조정이 필요합니다.",
        "common_causes": [
            "메모리 집약적 빌드 작업",
            "메모리 누수 (Memory Leak)",
            "대용량 파일 처리",
            "병렬 처리로 인한 메모리 사용량 증가",
            "JVM 힙 크기 부족",
            "컨테이너 메모리 제한 설정 문제"
        ],
        "checklist": [
            "💾 현재 메모리 사용률 확인",
            "📊 프로세스별 메모리 사용량 분석",
            "🔍 메모리 누수 패턴 조사",
            "⚙️ 빌드 도구 메모리 설정 검토",
            "🐳 컨테이너 리소스 제한 확인",
            "🔄 병렬 처리 설정 점검",
            "📈 메모리 사용 증가 추이 분석"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "메모리 사용량 진단",
                "commands": [
                    "free -h  # 전체 메모리 상태",
                    "top -o %MEM  # 메모리 사용량 순 프로세스",
                    "ps aux --sort=-%mem | head -20  # 메모리 Top 20",
                    "docker stats  # 컨테이너 메모리 사용량"
                ],
                "description": "현재 메모리 사용 상황을 상세히 분석합니다."
            },
            {
                "step": 2,
                "title": "메모리 설정 조정",
                "commands": [
                    "export MAVEN_OPTS='-Xmx4g -Xms2g'  # Maven JVM 메모리 증가",
                    "export NODE_OPTIONS='--max-old-space-size=4096'  # Node.js 메모리 증가",
                    "docker run --memory=8g ...  # Docker 메모리 제한 증가",
                    "ulimit -v 8388608  # 가상 메모리 제한 설정 (8GB)"
                ],
                "description": "빌드 도구별 메모리 설정을 조정합니다."
            },
            {
                "step": 3,
                "title": "메모리 사용 최적화",
                "commands": [
                    "# 병렬 처리 수준 조정",
                    "make -j2  # 동시 작업 수 제한",
                    "mvn -T 1  # Maven 스레드 수 제한",
                    "# 대용량 파일 스트리밍 처리",
                    "# 불필요한 메모리 캐시 비활성화"
                ],
                "description": "메모리 사용을 최적화하여 효율성을 높입니다."
            }
        ],
        "prevention_tips": [
            "적절한 메모리 제한 및 모니터링 설정",
            "메모리 사용 패턴 분석 및 최적화",
            "가비지 컬렉션 튜닝 (JVM 환경)",
            "메모리 효율적인 알고리즘 및 자료구조 사용"
        ],
        "related_links": [
            "https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html",
            "https://nodejs.org/api/cli.html#cli_max_old_space_size_size_in_megabytes",
            "https://docs.docker.com/config/containers/resource_constraints/"
        ]
    },

    "permission_denied": {
        "title": "🔐 권한 거부",
        "severity": "MEDIUM",
        "category": "SECURITY",
        "estimated_resolution_time": "10-20분",
        "description": "파일 또는 리소스에 대한 접근 권한이 부족합니다. 파일 권한, 사용자 권한, 또는 보안 정책 확인이 필요합니다.",
        "common_causes": [
            "파일 또는 디렉토리 권한 부족",
            "잘못된 사용자 컨텍스트로 실행",
            "SELinux 또는 AppArmor 정책 차단",
            "Docker 컨테이너 권한 제한",
            "네트워크 보안 그룹 규칙",
            "API 인증 토큰 만료 또는 권한 부족"
        ],
        "checklist": [
            "📁 파일/디렉토리 권한 확인",
            "👤 실행 사용자 및 그룹 검증",
            "🔒 보안 컨텍스트 (SELinux/AppArmor) 점검",
            "🐳 컨테이너 보안 설정 확인",
            "🔑 인증 토큰 및 자격 증명 검증",
            "🌐 네트워크 접근 권한 확인",
            "📋 정책 및 규칙 검토"
        ],
        "manual_actions": [
            {
                "step": 1,
                "title": "권한 상태 확인",
                "commands": [
                    "ls -la /path/to/file  # 파일 권한 확인",
                    "id  # 현재 사용자 정보",
                    "groups  # 사용자 그룹 확인",
                    "getcap /path/to/binary  # 바이너리 capability 확인"
                ],
                "description": "현재 권한 상태를 상세히 확인합니다."
            },
            {
                "step": 2,
                "title": "권한 수정",
                "commands": [
                    "chmod 755 /path/to/file  # 파일 권한 변경",
                    "chown user:group /path/to/file  # 소유자 변경",
                    "sudo usermod -aG docker $USER  # Docker 그룹 추가",
                    "newgrp docker  # 그룹 재로드"
                ],
                "description": "필요한 권한을 부여합니다."
            },
            {
                "step": 3,
                "title": "보안 컨텍스트 조정",
                "commands": [
                    "setenforce 0  # SELinux 임시 비활성화 (테스트용)",
                    "setsebool -P container_manage_cgroup on  # 컨테이너 권한",
                    "docker run --privileged ...  # 특권 모드 (주의 필요)",
                    "# 적절한 보안 정책 설정"
                ],
                "description": "보안 정책을 검토하고 필요시 조정합니다."
            }
        ],
        "prevention_tips": [
            "최소 권한 원칙 적용",
            "정기적인 권한 감사 및 검토",
            "자동화된 권한 관리 도구 사용",
            "보안 컨텍스트 모니터링"
        ],
        "related_links": [
            "https://docs.docker.com/engine/security/",
            "https://wiki.archlinux.org/title/File_permissions_and_attributes",
            "https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/using_selinux/"
        ]
    }
}


def get_runbook(error_code: str) -> Optional[Dict[str, Any]]:
    """
    특정 에러 코드에 대한 런북 정보를 반환합니다.

    Args:
        error_code (str): 에러 코드 (예: "dependency_install_failed")

    Returns:
        Optional[Dict[str, Any]]: 런북 정보 딕셔너리 또는 None
    """
    logger.debug(f"런북 조회 요청: {error_code}")

    if error_code in RUNBOOK_TEMPLATES:
        runbook = RUNBOOK_TEMPLATES[error_code].copy()
        runbook['error_code'] = error_code
        runbook['retrieved_at'] = datetime.now().isoformat()

        logger.info(f"런북 조회 성공: {error_code}")
        return runbook
    else:
        logger.warning(f"알 수 없는 에러 코드: {error_code}")
        return None


def render_markdown(error_code: str) -> str:
    """
    특정 에러 코드에 대한 런북을 Markdown 형식으로 렌더링합니다.

    Args:
        error_code (str): 에러 코드

    Returns:
        str: Markdown 형식의 런북 내용
    """
    runbook = get_runbook(error_code)

    if not runbook:
        return f"# ❌ 런북을 찾을 수 없음\n\n에러 코드 `{error_code}`에 대한 런북이 존재하지 않습니다."

    markdown_content = []

    # 제목 및 기본 정보
    markdown_content.append(f"# {runbook['title']}")
    markdown_content.append("")
    markdown_content.append(f"**에러 코드**: `{error_code}`")
    markdown_content.append(f"**심각도**: {runbook['severity']}")
    markdown_content.append(f"**카테고리**: {runbook['category']}")
    markdown_content.append(f"**예상 해결 시간**: {runbook['estimated_resolution_time']}")
    markdown_content.append(f"**조회 시간**: {runbook['retrieved_at']}")
    markdown_content.append("")

    # 설명
    markdown_content.append("## 📋 설명")
    markdown_content.append("")
    markdown_content.append(runbook['description'])
    markdown_content.append("")

    # 일반적인 원인
    markdown_content.append("## 🔍 일반적인 원인")
    markdown_content.append("")
    for cause in runbook['common_causes']:
        markdown_content.append(f"- {cause}")
    markdown_content.append("")

    # 체크리스트
    markdown_content.append("## ✅ 확인 체크리스트")
    markdown_content.append("")
    for item in runbook['checklist']:
        markdown_content.append(f"- [ ] {item}")
    markdown_content.append("")

    # 수동 조치
    markdown_content.append("## 🛠️ 수동 조치 단계")
    markdown_content.append("")
    for action in runbook['manual_actions']:
        markdown_content.append(f"### {action['step']}. {action['title']}")
        markdown_content.append("")
        markdown_content.append(action['description'])
        markdown_content.append("")

        if action['commands']:
            markdown_content.append("```bash")
            for command in action['commands']:
                markdown_content.append(command)
            markdown_content.append("```")
            markdown_content.append("")

    # 예방 팁
    markdown_content.append("## 💡 예방 팁")
    markdown_content.append("")
    for tip in runbook['prevention_tips']:
        markdown_content.append(f"- {tip}")
    markdown_content.append("")

    # 관련 링크
    if runbook['related_links']:
        markdown_content.append("## 🔗 관련 링크")
        markdown_content.append("")
        for link in runbook['related_links']:
            markdown_content.append(f"- {link}")
        markdown_content.append("")

    # 푸터
    markdown_content.append("---")
    markdown_content.append("")
    markdown_content.append("*이 런북은 자동으로 생성되었습니다. 내용이 부정확하거나 추가 정보가 필요한 경우 운영팀에 문의하세요.*")

    return "\n".join(markdown_content)


def get_all_error_codes() -> List[str]:
    """
    사용 가능한 모든 에러 코드 목록을 반환합니다.

    Returns:
        List[str]: 에러 코드 리스트
    """
    return list(RUNBOOK_TEMPLATES.keys())


def search_runbooks(keyword: str) -> List[Dict[str, Any]]:
    """
    키워드로 런북을 검색합니다.

    Args:
        keyword (str): 검색 키워드

    Returns:
        List[Dict[str, Any]]: 매칭된 런북 정보 리스트
    """
    keyword_lower = keyword.lower()
    results = []

    for error_code, runbook in RUNBOOK_TEMPLATES.items():
        # 제목, 설명, 카테고리에서 키워드 검색
        if (keyword_lower in runbook['title'].lower() or
            keyword_lower in runbook['description'].lower() or
            keyword_lower in runbook['category'].lower() or
            keyword_lower in error_code.lower()):

            result = {
                'error_code': error_code,
                'title': runbook['title'],
                'severity': runbook['severity'],
                'category': runbook['category'],
                'description': runbook['description'][:200] + "..." if len(runbook['description']) > 200 else runbook['description']
            }
            results.append(result)

    logger.info(f"런북 검색 완료: '{keyword}' - {len(results)}건 발견")
    return results


def get_runbook_summary() -> Dict[str, Any]:
    """
    전체 런북 데이터베이스 요약 정보를 반환합니다.

    Returns:
        Dict[str, Any]: 요약 정보
    """
    categories = {}
    severities = {}

    for error_code, runbook in RUNBOOK_TEMPLATES.items():
        # 카테고리별 집계
        category = runbook['category']
        if category not in categories:
            categories[category] = 0
        categories[category] += 1

        # 심각도별 집계
        severity = runbook['severity']
        if severity not in severities:
            severities[severity] = 0
        severities[severity] += 1

    return {
        'total_runbooks': len(RUNBOOK_TEMPLATES),
        'categories': categories,
        'severities': severities,
        'error_codes': list(RUNBOOK_TEMPLATES.keys()),
        'generated_at': datetime.now().isoformat()
    }


# 모듈 수준 함수들을 위한 편의 함수
def main():
    """
    테스트 및 데모용 메인 함수
    """
    print("🛠️ CI 에러 런북 시스템 테스트")
    print("=" * 50)

    # 전체 요약 정보
    summary = get_runbook_summary()
    print(f"📊 총 런북 수: {summary['total_runbooks']}")
    print(f"📂 카테고리: {', '.join(summary['categories'].keys())}")
    print(f"⚠️ 심각도: {', '.join(summary['severities'].keys())}")
    print()

    # 샘플 런북 조회
    sample_error = "dependency_install_failed"
    print(f"📋 샘플 런북 조회: {sample_error}")
    print("-" * 30)

    runbook = get_runbook(sample_error)
    if runbook:
        print(f"제목: {runbook['title']}")
        print(f"심각도: {runbook['severity']}")
        print(f"설명: {runbook['description'][:100]}...")
        print()

        # Markdown 렌더링 테스트
        print("📝 Markdown 렌더링 테스트:")
        markdown = render_markdown(sample_error)
        print(markdown[:500] + "...")

    # 검색 테스트
    print("\n🔍 검색 테스트: 'test'")
    search_results = search_runbooks("test")
    for result in search_results[:3]:
        print(f"- {result['error_code']}: {result['title']}")


if __name__ == "__main__":
    main()