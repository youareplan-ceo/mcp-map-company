#!/usr/bin/env python3
"""
StockPilot AI 보안 스캔 도구
코드 보안 취약점, 의존성 취약점, 설정 보안 문제를 종합적으로 검사
"""

import os
import re
import sys
import json
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import hashlib
import yaml

@dataclass
class SecurityFinding:
    """보안 발견사항"""
    severity: str  # critical, high, medium, low
    category: str  # dependency, code, config, credential
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    cve_id: Optional[str] = None
    recommendation: str = ""

class SecurityScanner:
    """보안 스캔 메인 클래스"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 민감한 정보 패턴
        self.sensitive_patterns = {
            'api_key': [
                r'api[_-]?key["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
                r'apikey["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
                r'["\']sk-[a-zA-Z0-9]{20,}["\']',  # OpenAI API 키
            ],
            'password': [
                r'password["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_@#$%^&*!]{8,}',
                r'passwd["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_@#$%^&*!]{8,}',
                r'pwd["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_@#$%^&*!]{8,}',
            ],
            'secret': [
                r'secret[_-]?key["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
                r'client[_-]?secret["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
            ],
            'token': [
                r'token["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
                r'access[_-]?token["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
                r'auth[_-]?token["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{10,}',
            ],
            'database_url': [
                r'postgres://[^:\s]*:[^@\s]*@[^/\s]*/[^\s]*',
                r'mysql://[^:\s]*:[^@\s]*@[^/\s]*/[^\s]*',
                r'mongodb://[^:\s]*:[^@\s]*@[^/\s]*/[^\s]*',
            ],
            'private_key': [
                r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
                r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
                r'-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----',
                r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----',
            ]
        }
        
        # 보안 취약점 패턴
        self.vulnerability_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*["\'].*%s.*["\']',
                r'query\s*\(\s*["\'].*%s.*["\']',
                r'cursor\.execute\s*\(\s*["\'].*\+.*["\']',
            ],
            'command_injection': [
                r'os\.system\s*\(\s*.*\+',
                r'subprocess\.call\s*\(\s*.*\+',
                r'subprocess\.run\s*\(\s*.*\+',
                r'os\.popen\s*\(\s*.*\+',
            ],
            'path_traversal': [
                r'open\s*\(\s*.*\+.*["\']\.\./',
                r'file\s*\(\s*.*\+.*["\']\.\./',
            ],
            'deserialization': [
                r'pickle\.loads?\s*\(',
                r'yaml\.load\s*\(',
                r'eval\s*\(',
                r'exec\s*\(',
            ],
            'weak_crypto': [
                r'hashlib\.md5\s*\(',
                r'hashlib\.sha1\s*\(',
                r'random\.random\s*\(',  # 암호학적으로 안전하지 않은 랜덤
            ]
        }
        
        # 안전하지 않은 설정 패턴
        self.insecure_config_patterns = {
            'debug_mode': [
                r'DEBUG\s*=\s*True',
                r'debug\s*=\s*true',
                r'DEBUG\s*=\s*1',
            ],
            'insecure_cors': [
                r'CORS_ALLOW_ALL_ORIGINS\s*=\s*True',
                r'Access-Control-Allow-Origin.*\*',
            ],
            'weak_session': [
                r'SESSION_COOKIE_SECURE\s*=\s*False',
                r'SESSION_COOKIE_HTTPONLY\s*=\s*False',
            ]
        }

    def scan_all(self) -> Dict:
        """전체 보안 스캔 실행"""
        self.logger.info("보안 스캔 시작")
        
        # 1. 의존성 취약점 스캔
        self.scan_dependencies()
        
        # 2. 코드 보안 스캔
        self.scan_code_vulnerabilities()
        
        # 3. 자격 증명 스캔
        self.scan_credentials()
        
        # 4. 설정 보안 스캔
        self.scan_configurations()
        
        # 5. Docker 이미지 스캔 (있는 경우)
        self.scan_docker_images()
        
        # 결과 생성
        return self.generate_report()

    def scan_dependencies(self):
        """의존성 취약점 스캔"""
        self.logger.info("의존성 취약점 스캔 중...")
        
        # Python 의존성 스캔
        python_files = [
            self.project_root / "requirements.txt",
            self.project_root / "backend" / "requirements.txt",
            self.project_root / "ai_engine" / "requirements.txt",
        ]
        
        for req_file in python_files:
            if req_file.exists():
                self._scan_python_dependencies(req_file)
        
        # Node.js 의존성 스캔
        package_json_files = [
            self.project_root / "package.json",
            self.project_root / "frontend" / "package.json",
        ]
        
        for package_file in package_json_files:
            if package_file.exists():
                self._scan_nodejs_dependencies(package_file)

    def _scan_python_dependencies(self, requirements_file: Path):
        """Python 의존성 보안 스캔"""
        try:
            # safety를 사용한 의존성 스캔 시도
            result = subprocess.run(
                ["safety", "check", "-r", str(requirements_file), "--json"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and result.stdout:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self.findings.append(SecurityFinding(
                        severity="high" if vuln.get("vulnerability_id") else "medium",
                        category="dependency",
                        title=f"취약한 Python 패키지: {vuln.get('package')}",
                        description=vuln.get('advisory', '알려진 보안 취약점'),
                        file_path=str(requirements_file),
                        cve_id=vuln.get("cve"),
                        recommendation=f"패키지를 {vuln.get('safe_version', '최신 버전')}으로 업데이트하세요"
                    ))
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # safety가 설치되지 않은 경우 기본 검사 수행
            self._basic_python_dependency_check(requirements_file)

    def _basic_python_dependency_check(self, requirements_file: Path):
        """기본 Python 의존성 검사"""
        known_vulnerabilities = {
            'django<3.2.13': 'CVE-2022-28346: SQL injection vulnerability',
            'flask<2.2.2': 'CVE-2022-37434: Potential DoS vulnerability',
            'requests<2.28.0': 'CVE-2022-32149: Potential certificate verification bypass',
            'numpy<1.22.0': 'CVE-2021-33430: Buffer overflow vulnerability',
            'pillow<9.1.1': 'CVE-2022-30595: Potential buffer overflow',
        }
        
        content = requirements_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                for vuln_pattern, description in known_vulnerabilities.items():
                    if self._matches_dependency_pattern(line, vuln_pattern):
                        self.findings.append(SecurityFinding(
                            severity="medium",
                            category="dependency",
                            title=f"알려진 취약점이 있는 패키지",
                            description=description,
                            file_path=str(requirements_file),
                            recommendation="패키지를 최신 안전한 버전으로 업데이트하세요"
                        ))

    def _matches_dependency_pattern(self, requirement: str, pattern: str) -> bool:
        """의존성 패턴 매칭"""
        # 간단한 버전 비교 로직
        import re
        package_match = re.match(r'^([a-zA-Z0-9_-]+)([<>=!]+)(.+)$', pattern)
        if not package_match:
            return False
            
        pattern_name, operator, pattern_version = package_match.groups()
        
        req_match = re.match(r'^([a-zA-Z0-9_-]+)([<>=!]*)(.*)$', requirement.replace('==', '='))
        if not req_match:
            return False
            
        req_name, req_operator, req_version = req_match.groups()
        
        return req_name.lower() == pattern_name.lower()

    def _scan_nodejs_dependencies(self, package_file: Path):
        """Node.js 의존성 보안 스캔"""
        try:
            package_dir = package_file.parent
            
            # npm audit 실행
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=package_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.stdout:
                try:
                    audit_data = json.loads(result.stdout)
                    if 'vulnerabilities' in audit_data:
                        for vuln_name, vuln_data in audit_data['vulnerabilities'].items():
                            severity = vuln_data.get('severity', 'medium')
                            self.findings.append(SecurityFinding(
                                severity=severity,
                                category="dependency",
                                title=f"취약한 Node.js 패키지: {vuln_name}",
                                description=vuln_data.get('title', '알려진 보안 취약점'),
                                file_path=str(package_file),
                                recommendation="npm audit fix를 실행하거나 패키지를 업데이트하세요"
                            ))
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("npm audit를 실행할 수 없습니다")

    def scan_code_vulnerabilities(self):
        """코드 보안 취약점 스캔"""
        self.logger.info("코드 보안 취약점 스캔 중...")
        
        # 스캔할 파일 확장자
        extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.yaml', '.yml', '.json']
        
        for ext in extensions:
            files = self.project_root.rglob(f'*{ext}')
            for file_path in files:
                # 제외할 디렉토리
                if any(part in file_path.parts for part in ['node_modules', '.git', '__pycache__', 'venv']):
                    continue
                    
                self._scan_file_vulnerabilities(file_path)

    def _scan_file_vulnerabilities(self, file_path: Path):
        """개별 파일의 보안 취약점 스캔"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for category, patterns in self.vulnerability_patterns.items():
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            severity = self._get_vulnerability_severity(category)
                            self.findings.append(SecurityFinding(
                                severity=severity,
                                category="code",
                                title=f"보안 취약점: {category}",
                                description=self._get_vulnerability_description(category),
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                recommendation=self._get_vulnerability_recommendation(category)
                            ))
                            
        except (UnicodeDecodeError, PermissionError):
            pass

    def scan_credentials(self):
        """자격 증명 스캔"""
        self.logger.info("자격 증명 스캔 중...")
        
        # 스캔할 파일 타입
        extensions = ['.py', '.js', '.ts', '.env', '.yaml', '.yml', '.json', '.txt', '.md']
        
        for ext in extensions:
            files = self.project_root.rglob(f'*{ext}')
            for file_path in files:
                # 제외할 파일/디렉토리
                if any(part in file_path.parts for part in ['node_modules', '.git', '__pycache__', 'venv']):
                    continue
                if file_path.name.endswith('.example'):
                    continue
                    
                self._scan_file_credentials(file_path)

    def _scan_file_credentials(self, file_path: Path):
        """파일에서 자격 증명 스캔"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for cred_type, patterns in self.sensitive_patterns.items():
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        if matches:
                            # 예시 값이나 플레이스홀더 제외
                            if self._is_placeholder(line):
                                continue
                                
                            self.findings.append(SecurityFinding(
                                severity="critical",
                                category="credential",
                                title=f"하드코딩된 자격증명: {cred_type}",
                                description=f"파일에 {cred_type}이(가) 하드코딩되어 있습니다",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                recommendation="자격증명을 환경 변수나 보안 저장소로 이동하세요"
                            ))
                            
        except (UnicodeDecodeError, PermissionError):
            pass

    def _is_placeholder(self, line: str) -> bool:
        """플레이스홀더나 예시 값인지 확인"""
        placeholder_indicators = [
            'example', 'placeholder', 'your_', 'change_', 'replace_',
            'xxx', 'yyy', 'zzz', '123', 'test', 'demo', 'sample',
            'fake', 'dummy', '<', '>', '{', '}', 'TODO', 'FIXME'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in placeholder_indicators)

    def scan_configurations(self):
        """설정 보안 스캔"""
        self.logger.info("설정 보안 스캔 중...")
        
        # 설정 파일들
        config_files = [
            self.project_root / "settings.py",
            self.project_root / "config.py",
            self.project_root / "backend" / "app" / "config.py",
            self.project_root / "backend" / "settings.py",
            self.project_root / ".env",
            self.project_root / ".env.local",
            self.project_root / "docker-compose.yml",
            self.project_root / "nginx.conf",
        ]
        
        for config_file in config_files:
            if config_file.exists():
                self._scan_configuration_file(config_file)

    def _scan_configuration_file(self, config_file: Path):
        """설정 파일 보안 검사"""
        try:
            content = config_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for config_type, patterns in self.insecure_config_patterns.items():
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.findings.append(SecurityFinding(
                                severity="medium",
                                category="config",
                                title=f"안전하지 않은 설정: {config_type}",
                                description=self._get_config_description(config_type),
                                file_path=str(config_file.relative_to(self.project_root)),
                                line_number=line_num,
                                recommendation=self._get_config_recommendation(config_type)
                            ))
                            
        except (UnicodeDecodeError, PermissionError):
            pass

    def scan_docker_images(self):
        """Docker 이미지 보안 스캔"""
        self.logger.info("Docker 이미지 스캔 중...")
        
        dockerfile_paths = list(self.project_root.rglob("Dockerfile*"))
        
        for dockerfile in dockerfile_paths:
            self._scan_dockerfile(dockerfile)

    def _scan_dockerfile(self, dockerfile: Path):
        """Dockerfile 보안 검사"""
        try:
            content = dockerfile.read_text()
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # ROOT 사용자 검사
                if line.upper().startswith('USER ROOT') or 'USER 0' in line:
                    self.findings.append(SecurityFinding(
                        severity="medium",
                        category="config",
                        title="Docker: ROOT 사용자 사용",
                        description="컨테이너가 root 권한으로 실행됩니다",
                        file_path=str(dockerfile.relative_to(self.project_root)),
                        line_number=line_num,
                        recommendation="non-root 사용자를 생성하고 사용하세요"
                    ))
                
                # 비밀 정보가 포함된 ADD/COPY 검사
                if line.upper().startswith(('ADD', 'COPY')) and any(secret in line.lower() for secret in ['.env', 'secret', 'key', 'password']):
                    self.findings.append(SecurityFinding(
                        severity="high",
                        category="config",
                        title="Docker: 민감한 파일 복사",
                        description="민감한 정보가 포함된 파일이 이미지에 포함될 수 있습니다",
                        file_path=str(dockerfile.relative_to(self.project_root)),
                        line_number=line_num,
                        recommendation=".dockerignore를 사용하거나 빌드 시 제외하세요"
                    ))
                    
        except (UnicodeDecodeError, PermissionError):
            pass

    def _get_vulnerability_severity(self, category: str) -> str:
        """취약점 카테고리별 심각도 반환"""
        severity_map = {
            'sql_injection': 'critical',
            'command_injection': 'critical',
            'path_traversal': 'high',
            'deserialization': 'high',
            'weak_crypto': 'medium'
        }
        return severity_map.get(category, 'medium')

    def _get_vulnerability_description(self, category: str) -> str:
        """취약점 설명 반환"""
        descriptions = {
            'sql_injection': 'SQL 인젝션 공격에 취약할 수 있습니다',
            'command_injection': '명령어 인젝션 공격에 취약할 수 있습니다',
            'path_traversal': '경로 순회 공격에 취약할 수 있습니다',
            'deserialization': '비안전한 역직렬화로 인한 보안 위험이 있습니다',
            'weak_crypto': '약한 암호화 알고리즘을 사용하고 있습니다'
        }
        return descriptions.get(category, '알려진 보안 취약점이 있습니다')

    def _get_vulnerability_recommendation(self, category: str) -> str:
        """취약점 수정 권장사항 반환"""
        recommendations = {
            'sql_injection': 'parameterized query나 ORM을 사용하세요',
            'command_injection': '사용자 입력을 검증하고 안전한 API를 사용하세요',
            'path_traversal': '경로를 검증하고 chroot를 사용하세요',
            'deserialization': 'pickle 대신 JSON을 사용하거나 신뢰할 수 있는 데이터만 역직렬화하세요',
            'weak_crypto': 'SHA-256 이상의 강한 해시 알고리즘을 사용하세요'
        }
        return recommendations.get(category, '보안 모범 사례를 따르세요')

    def _get_config_description(self, config_type: str) -> str:
        """설정 문제 설명 반환"""
        descriptions = {
            'debug_mode': '디버그 모드가 활성화되어 민감한 정보가 노출될 수 있습니다',
            'insecure_cors': 'CORS 설정이 모든 도메인을 허용하여 보안 위험이 있습니다',
            'weak_session': '세션 쿠키 보안 설정이 약화되어 있습니다'
        }
        return descriptions.get(config_type, '안전하지 않은 설정입니다')

    def _get_config_recommendation(self, config_type: str) -> str:
        """설정 수정 권장사항 반환"""
        recommendations = {
            'debug_mode': '프로덕션에서는 DEBUG=False로 설정하세요',
            'insecure_cors': '특정 도메인만 허용하도록 CORS를 설정하세요',
            'weak_session': 'SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True로 설정하세요'
        }
        return recommendations.get(config_type, '보안 설정을 강화하세요')

    def generate_report(self) -> Dict:
        """보안 스캔 결과 리포트 생성"""
        # 심각도별 통계
        severity_counts = {}
        category_counts = {}
        
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        
        # 전체 점수 계산 (100점 만점)
        total_score = 100
        severity_penalties = {'critical': 20, 'high': 10, 'medium': 5, 'low': 2}
        
        for finding in self.findings:
            penalty = severity_penalties.get(finding.severity, 0)
            total_score = max(0, total_score - penalty)
        
        # 보안 등급 계산
        if total_score >= 90:
            grade = 'A'
        elif total_score >= 80:
            grade = 'B'
        elif total_score >= 70:
            grade = 'C'
        elif total_score >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        report = {
            'scan_info': {
                'timestamp': datetime.now().isoformat(),
                'project_root': str(self.project_root),
                'total_files_scanned': len(list(self.project_root.rglob('*.*'))),
                'scan_duration': '알 수 없음'  # TODO: 시간 측정 추가
            },
            'summary': {
                'total_findings': len(self.findings),
                'severity_counts': severity_counts,
                'category_counts': category_counts,
                'security_score': total_score,
                'security_grade': grade
            },
            'findings': [asdict(finding) for finding in self.findings],
            'recommendations': self._generate_recommendations()
        }
        
        return report

    def _generate_recommendations(self) -> List[str]:
        """전체적인 보안 권장사항 생성"""
        recommendations = []
        
        # 심각도별 권장사항
        if any(f.severity == 'critical' for f in self.findings):
            recommendations.append("🚨 치명적인 보안 문제가 발견되었습니다. 즉시 수정하세요.")
        
        if any(f.category == 'credential' for f in self.findings):
            recommendations.append("🔑 하드코딩된 자격증명을 환경변수나 보안 저장소로 이전하세요.")
        
        if any(f.category == 'dependency' for f in self.findings):
            recommendations.append("📦 취약한 의존성 패키지를 최신 안전한 버전으로 업데이트하세요.")
        
        if any(f.category == 'code' for f in self.findings):
            recommendations.append("🛡️ 코드에서 발견된 보안 취약점을 수정하세요.")
        
        if any(f.category == 'config' for f in self.findings):
            recommendations.append("⚙️ 안전하지 않은 설정을 보안 모범사례에 따라 수정하세요.")
        
        # 일반적인 권장사항
        recommendations.extend([
            "🔍 정기적인 보안 스캔을 수행하세요.",
            "📚 팀원들에게 보안 코딩 교육을 제공하세요.",
            "🔒 코드 리뷰에서 보안 관점을 포함하세요.",
            "📋 보안 체크리스트를 배포 프로세스에 포함하세요."
        ])
        
        return recommendations

    def save_report(self, report: Dict, output_file: str = None):
        """리포트를 파일로 저장"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"security_scan_report_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"보안 스캔 리포트가 저장되었습니다: {output_file}")
        
        # HTML 리포트도 생성
        html_file = output_file.replace('.json', '.html')
        self._generate_html_report(report, html_file)

    def _generate_html_report(self, report: Dict, output_file: str):
        """HTML 형태의 리포트 생성"""
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockPilot AI 보안 스캔 리포트</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5; 
        }
        .container { 
            max-width: 1200px; margin: 0 auto; background: white; 
            border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .grade { font-size: 48px; font-weight: bold; margin: 10px 0; }
        .grade.A, .grade.B { color: #28a745; }
        .grade.C { color: #ffc107; }
        .grade.D, .grade.F { color: #dc3545; }
        .summary { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }
        .stat-card { 
            background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; 
        }
        .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
        .findings { margin-top: 30px; }
        .finding { 
            border: 1px solid #ddd; margin-bottom: 15px; border-radius: 6px; 
            padding: 20px; background: white;
        }
        .severity { 
            display: inline-block; padding: 4px 8px; border-radius: 4px; 
            color: white; font-size: 12px; font-weight: bold; text-transform: uppercase;
        }
        .severity.critical { background: #dc3545; }
        .severity.high { background: #fd7e14; }
        .severity.medium { background: #ffc107; color: #212529; }
        .severity.low { background: #28a745; }
        .category { 
            display: inline-block; padding: 4px 8px; border-radius: 4px; 
            background: #e9ecef; color: #495057; font-size: 12px; margin-left: 10px;
        }
        .recommendations { 
            background: #e7f3ff; border: 1px solid #bee5eb; 
            border-radius: 6px; padding: 20px; margin-top: 30px; 
        }
        .file-path { 
            font-family: monospace; background: #f8f9fa; 
            padding: 2px 6px; border-radius: 3px; font-size: 14px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ StockPilot AI 보안 스캔 리포트</h1>
            <div class="grade {grade}">{grade}</div>
            <p>보안 점수: {security_score}/100</p>
            <p>스캔 일시: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number">{total_findings}</div>
                <div>총 발견사항</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{critical_count}</div>
                <div>치명적</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{high_count}</div>
                <div>높음</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{medium_count}</div>
                <div>보통</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{low_count}</div>
                <div>낮음</div>
            </div>
        </div>
        
        <div class="findings">
            <h2>🔍 발견사항</h2>
            {findings_html}
        </div>
        
        <div class="recommendations">
            <h2>💡 권장사항</h2>
            {recommendations_html}
        </div>
    </div>
</body>
</html>
"""
        
        # 발견사항 HTML 생성
        findings_html = ""
        for finding in report['findings']:
            findings_html += f"""
            <div class="finding">
                <div>
                    <span class="severity {finding['severity']}">{finding['severity']}</span>
                    <span class="category">{finding['category']}</span>
                </div>
                <h3>{finding['title']}</h3>
                <p>{finding['description']}</p>
                <p><strong>파일:</strong> <span class="file-path">{finding['file_path']}</span>
                {f" (라인 {finding['line_number']})" if finding['line_number'] else ""}
                </p>
                {f"<p><strong>CVE:</strong> {finding['cve_id']}</p>" if finding['cve_id'] else ""}
                <p><strong>권장사항:</strong> {finding['recommendation']}</p>
            </div>
            """
        
        # 권장사항 HTML 생성
        recommendations_html = "<ul>"
        for rec in report['recommendations']:
            recommendations_html += f"<li>{rec}</li>"
        recommendations_html += "</ul>"
        
        # 템플릿 변수 치환
        html_content = html_template.format(
            grade=report['summary']['security_grade'],
            security_score=report['summary']['security_score'],
            timestamp=report['scan_info']['timestamp'],
            total_findings=report['summary']['total_findings'],
            critical_count=report['summary']['severity_counts'].get('critical', 0),
            high_count=report['summary']['severity_counts'].get('high', 0),
            medium_count=report['summary']['severity_counts'].get('medium', 0),
            low_count=report['summary']['severity_counts'].get('low', 0),
            findings_html=findings_html,
            recommendations_html=recommendations_html
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML 리포트가 생성되었습니다: {output_file}")

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='StockPilot AI 보안 스캔 도구')
    parser.add_argument('--project-root', '-p', default='.', help='프로젝트 루트 디렉토리')
    parser.add_argument('--output', '-o', help='출력 파일명')
    parser.add_argument('--format', choices=['json', 'html', 'both'], default='both', help='출력 형식')
    parser.add_argument('--severity', choices=['critical', 'high', 'medium', 'low'], help='최소 심각도 필터')
    parser.add_argument('--category', choices=['dependency', 'code', 'config', 'credential'], help='카테고리 필터')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 보안 스캔 실행
    scanner = SecurityScanner(args.project_root)
    report = scanner.scan_all()
    
    # 필터 적용
    if args.severity or args.category:
        filtered_findings = []
        severity_order = ['low', 'medium', 'high', 'critical']
        min_severity_idx = severity_order.index(args.severity) if args.severity else 0
        
        for finding_dict in report['findings']:
            finding_severity_idx = severity_order.index(finding_dict['severity'])
            
            # 심각도 필터
            if finding_severity_idx < min_severity_idx:
                continue
                
            # 카테고리 필터
            if args.category and finding_dict['category'] != args.category:
                continue
                
            filtered_findings.append(finding_dict)
        
        report['findings'] = filtered_findings
        report['summary']['total_findings'] = len(filtered_findings)
    
    # 결과 출력
    if args.format in ['json', 'both']:
        output_file = args.output or f"security_scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        scanner.save_report(report, output_file)
    
    if args.format in ['html', 'both']:
        html_file = args.output.replace('.json', '.html') if args.output else f"security_scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        scanner._generate_html_report(report, html_file)
    
    # 콘솔 요약 출력
    print(f"\n🛡️  보안 스캔 완료")
    print(f"보안 점수: {report['summary']['security_score']}/100 (등급: {report['summary']['security_grade']})")
    print(f"총 발견사항: {report['summary']['total_findings']}개")
    
    if report['summary']['severity_counts']:
        print("심각도별 분포:")
        for severity, count in report['summary']['severity_counts'].items():
            print(f"  {severity}: {count}개")
    
    # 종료 코드 반환
    if report['summary']['total_findings'] == 0:
        print("✅ 보안 문제가 발견되지 않았습니다.")
        return 0
    elif any(f['severity'] == 'critical' for f in report['findings']):
        print("🚨 치명적인 보안 문제가 발견되었습니다!")
        return 2
    elif any(f['severity'] == 'high' for f in report['findings']):
        print("⚠️  높은 수준의 보안 문제가 발견되었습니다.")
        return 1
    else:
        print("ℹ️  일부 보안 개선사항이 있습니다.")
        return 0

if __name__ == "__main__":
    sys.exit(main())