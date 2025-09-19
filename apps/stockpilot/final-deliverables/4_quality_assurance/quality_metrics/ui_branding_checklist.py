#!/usr/bin/env python3
"""
StockPilot AI UI 브랜딩 최종 확인 & 교체 체크리스트
모든 UI 요소에서 StockPilot 브랜딩이 올바르게 적용되었는지 검증
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

class UIBrandingChecker:
    """UI 브랜딩 확인 및 검증 클래스"""
    
    def __init__(self):
        self.frontend_path = Path('/Users/youareplan/stockpilot-ai/frontend')
        self.backend_path = Path('/Users/youareplan/stockpilot-ai/backend')
        
        self.results = {
            'total_files_checked': 0,
            'branding_issues': [],
            'correct_branding': [],
            'recommendations': [],
            'file_analysis': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # 브랜딩 패턴 정의
        self.correct_patterns = [
            'StockPilot',
            'stockpilot-ai',
            'Stock Pilot',
            'STOCK PILOT'
        ]
        
        self.incorrect_patterns = [
            'React App',
            'Create React App',
            'CRA',
            'My React App',
            'Untitled',
            'App',
            'Test App',
            'Sample App'
        ]
        
        # 체크할 파일 패턴
        self.file_patterns = [
            '**/*.tsx',
            '**/*.ts', 
            '**/*.js',
            '**/*.jsx',
            '**/*.json',
            '**/*.html',
            '**/*.md',
            '**/*.yml',
            '**/*.yaml',
            '**/package.json',
            '**/*.env*'
        ]
        
    def run_branding_check(self) -> Dict[str, Any]:
        """전체 브랜딩 체크리스트 실행"""
        print("🎨 StockPilot AI UI 브랜딩 최종 확인 시작")
        
        # 1. 메타데이터 확인
        self._check_metadata_branding()
        
        # 2. 소스 코드 브랜딩 확인
        self._check_source_code_branding()
        
        # 3. 설정 파일 브랜딩 확인
        self._check_config_files_branding()
        
        # 4. 문서 브랜딩 확인
        self._check_documentation_branding()
        
        # 5. API 응답 브랜딩 확인
        self._check_api_branding()
        
        # 6. 환경 설정 브랜딩 확인
        self._check_environment_branding()
        
        # 결과 분석 및 보고서 생성
        self._analyze_results()
        
        print(f"✅ 브랜딩 체크 완료: {len(self.results['correct_branding'])}개 정상, {len(self.results['branding_issues'])}개 이슈")
        
        return self.results
    
    def _check_metadata_branding(self):
        """메타데이터 브랜딩 확인 (package.json, index.html 등)"""
        print("📋 메타데이터 브랜딩 확인")
        
        # package.json 확인
        package_json_path = self.frontend_path / 'package.json'
        if package_json_path.exists():
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                
            # name, description, homepage 확인
            fields_to_check = ['name', 'description', 'homepage', 'author']
            for field in fields_to_check:
                if field in package_data:
                    value = package_data[field]
                    self._analyze_branding_text(f"package.json:{field}", value)
        
        # index.html 확인
        index_html_path = self.frontend_path / 'public' / 'index.html'
        if index_html_path.exists():
            with open(index_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # title, description 메타태그 확인
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
            if title_match:
                self._analyze_branding_text("index.html:title", title_match.group(1))
            
            # 메타 설명 확인
            meta_desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            if meta_desc_match:
                self._analyze_branding_text("index.html:meta_description", meta_desc_match.group(1))
    
    def _check_source_code_branding(self):
        """소스 코드 내 브랜딩 확인"""
        print("💻 소스 코드 브랜딩 확인")
        
        # 주요 컴포넌트 파일 확인
        key_files = [
            'src/App.tsx',
            'src/components/ui/Logo.jsx',
            'src/components/common/Layout.tsx',
            'src/pages/Dashboard.tsx',
            'src/i18n/locales/ko.js'
        ]
        
        for file_path in key_files:
            full_path = self.frontend_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 브랜딩 패턴 분석
                self._analyze_file_branding(file_path, content)
    
    def _check_config_files_branding(self):
        """설정 파일 브랜딩 확인"""
        print("⚙️ 설정 파일 브랜딩 확인")
        
        config_files = [
            '.env.example',
            '.env.production',
            'craco.config.js',
            'nginx/nginx.conf'
        ]
        
        for file_path in config_files:
            full_path = self.frontend_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._analyze_file_branding(f"config/{file_path}", content)
    
    def _check_documentation_branding(self):
        """문서 브랜딩 확인"""
        print("📚 문서 브랜딩 확인")
        
        doc_files = [
            'README.md',
            '../backend/README.md'
        ]
        
        for file_path in doc_files:
            if file_path.startswith('../'):
                full_path = self.frontend_path / file_path
            else:
                full_path = self.frontend_path / file_path
                
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._analyze_file_branding(f"docs/{file_path}", content)
    
    def _check_api_branding(self):
        """API 응답 브랜딩 확인"""
        print("🔌 API 브랜딩 확인")
        
        # API 엔드포인트 파일 확인
        api_files = [
            '../backend/api_endpoints.py',
            '../backend/websocket_server.py',
            '../backend/dashboard_api.py'
        ]
        
        for file_path in api_files:
            full_path = self.frontend_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._analyze_file_branding(f"api/{file_path}", content)
    
    def _check_environment_branding(self):
        """환경 설정 브랜딩 확인"""
        print("🌍 환경 설정 브랜딩 확인")
        
        # 배포 설정 파일 확인
        deploy_files = [
            'render.yaml',
            'vercel.json',
            'Dockerfile',
            'docker-compose.yml'
        ]
        
        # 루트 디렉토리에서 확인
        root_path = self.frontend_path.parent
        for file_path in deploy_files:
            full_path = root_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self._analyze_file_branding(f"deploy/{file_path}", content)
    
    def _analyze_branding_text(self, location: str, text: str):
        """텍스트에서 브랜딩 패턴 분석"""
        text_lower = text.lower()
        
        # 올바른 브랜딩 패턴 확인
        correct_found = any(pattern.lower() in text_lower for pattern in self.correct_patterns)
        
        # 잘못된 브랜딩 패턴 확인
        incorrect_found = []
        for pattern in self.incorrect_patterns:
            if pattern.lower() in text_lower:
                incorrect_found.append(pattern)
        
        if incorrect_found:
            self.results['branding_issues'].append({
                'location': location,
                'text': text,
                'issues': incorrect_found,
                'severity': 'high' if 'react app' in text_lower else 'medium'
            })
        elif correct_found:
            self.results['correct_branding'].append({
                'location': location,
                'text': text,
                'patterns_found': [p for p in self.correct_patterns if p.lower() in text_lower]
            })
        else:
            # 브랜딩이 명확하지 않은 경우
            if len(text.strip()) > 0:
                self.results['branding_issues'].append({
                    'location': location,
                    'text': text,
                    'issues': ['Generic or unclear branding'],
                    'severity': 'low'
                })
    
    def _analyze_file_branding(self, file_path: str, content: str):
        """파일 전체에서 브랜딩 패턴 분석"""
        self.results['total_files_checked'] += 1
        
        # 각 라인별로 브랜딩 검사
        lines = content.split('\n')
        file_issues = []
        file_correct = []
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if len(line_stripped) > 5:  # 의미있는 라인만 검사
                
                # 주석이나 문자열에서 브랜딩 패턴 찾기
                if any(keyword in line_stripped for keyword in ['title', 'name', 'description', 'brand', 'app']):
                    
                    # 올바른 브랜딩 확인
                    correct_patterns_found = [p for p in self.correct_patterns if p in line]
                    if correct_patterns_found:
                        file_correct.append({
                            'line': line_num,
                            'content': line_stripped,
                            'patterns': correct_patterns_found
                        })
                    
                    # 잘못된 브랜딩 확인
                    incorrect_patterns_found = [p for p in self.incorrect_patterns if p.lower() in line.lower()]
                    if incorrect_patterns_found:
                        file_issues.append({
                            'line': line_num,
                            'content': line_stripped,
                            'issues': incorrect_patterns_found
                        })
        
        # 파일 분석 결과 저장
        self.results['file_analysis'][file_path] = {
            'total_lines': len(lines),
            'issues_found': len(file_issues),
            'correct_branding_found': len(file_correct),
            'issues': file_issues,
            'correct': file_correct
        }
        
        # 전체 결과에 추가
        if file_issues:
            self.results['branding_issues'].extend([{
                'location': f"{file_path}:{issue['line']}",
                'text': issue['content'],
                'issues': issue['issues'],
                'severity': 'medium'
            } for issue in file_issues])
        
        if file_correct:
            self.results['correct_branding'].extend([{
                'location': f"{file_path}:{correct['line']}",
                'text': correct['content'],
                'patterns_found': correct['patterns']
            } for correct in file_correct])
    
    def _analyze_results(self):
        """결과 분석 및 추천사항 생성"""
        total_issues = len(self.results['branding_issues'])
        total_correct = len(self.results['correct_branding'])
        
        # 심각도별 이슈 분류
        high_severity = len([i for i in self.results['branding_issues'] if i['severity'] == 'high'])
        medium_severity = len([i for i in self.results['branding_issues'] if i['severity'] == 'medium'])
        low_severity = len([i for i in self.results['branding_issues'] if i['severity'] == 'low'])
        
        # 브랜딩 스코어 계산
        if total_issues + total_correct > 0:
            branding_score = (total_correct / (total_issues + total_correct)) * 100
        else:
            branding_score = 0
        
        self.results['summary'] = {
            'total_files_checked': self.results['total_files_checked'],
            'total_issues': total_issues,
            'total_correct': total_correct,
            'branding_score': round(branding_score, 2),
            'severity_breakdown': {
                'high': high_severity,
                'medium': medium_severity,
                'low': low_severity
            }
        }
        
        # 추천사항 생성
        recommendations = []
        
        if high_severity > 0:
            recommendations.append("🚨 HIGH: 즉시 수정 필요 - 'React App' 등 기본 브랜딩을 StockPilot으로 교체")
        
        if medium_severity > 0:
            recommendations.append("⚠️ MEDIUM: 브랜딩 일관성 개선 - 모든 UI 요소에서 StockPilot 브랜딩 통일")
        
        if low_severity > 0:
            recommendations.append("ℹ️ LOW: 브랜딩 명확성 개선 - 애매한 표현을 StockPilot 브랜딩으로 명시")
        
        if branding_score >= 90:
            recommendations.append("✨ 브랜딩 상태가 매우 우수합니다!")
        elif branding_score >= 70:
            recommendations.append("👍 브랜딩 상태가 양호합니다. 소수 이슈만 수정하면 완벽!")
        else:
            recommendations.append("📝 브랜딩 개선이 필요합니다. 체계적인 브랜딩 업데이트 권장")
        
        # 구체적 수정 가이드
        recommendations.extend([
            "🔧 수정 가이드:",
            "  1. HTML title 태그: 'StockPilot - AI 투자 코파일럿'",
            "  2. package.json name: 'stockpilot-ai-frontend'", 
            "  3. 로고/브랜드명: 일관되게 'StockPilot' 사용",
            "  4. 설명문: 'AI 기반 투자 코파일럿 플랫폼'",
            "  5. 환경 변수: REACT_APP_NAME=StockPilot"
        ])
        
        self.results['recommendations'] = recommendations
    
    def generate_report(self) -> str:
        """브랜딩 체크리스트 보고서 생성"""
        report = []
        report.append("=" * 80)
        report.append("🎨 StockPilot AI UI 브랜딩 최종 확인 보고서")
        report.append("=" * 80)
        report.append(f"검사 일시: {self.results['timestamp']}")
        report.append(f"검사 파일 수: {self.results['summary']['total_files_checked']}")
        report.append(f"브랜딩 점수: {self.results['summary']['branding_score']}%")
        report.append("")
        
        # 요약 통계
        summary = self.results['summary']
        report.append("📊 요약 통계:")
        report.append(f"  ✅ 올바른 브랜딩: {summary['total_correct']}건")
        report.append(f"  ❌ 브랜딩 이슈: {summary['total_issues']}건")
        report.append(f"    - 높음: {summary['severity_breakdown']['high']}건")
        report.append(f"    - 보통: {summary['severity_breakdown']['medium']}건")
        report.append(f"    - 낮음: {summary['severity_breakdown']['low']}건")
        report.append("")
        
        # 주요 이슈
        if self.results['branding_issues']:
            report.append("🚨 주요 브랜딩 이슈:")
            for issue in self.results['branding_issues'][:10]:  # 상위 10개만 표시
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}[issue['severity']]
                report.append(f"  {severity_icon} {issue['location']}")
                report.append(f"    내용: {issue['text'][:100]}...")
                report.append(f"    이슈: {', '.join(issue['issues'])}")
                report.append("")
        
        # 올바른 브랜딩 예시
        if self.results['correct_branding']:
            report.append("✅ 올바른 브랜딩 예시:")
            for correct in self.results['correct_branding'][:5]:  # 상위 5개만 표시
                report.append(f"  📍 {correct['location']}")
                report.append(f"    내용: {correct['text'][:100]}...")
                report.append(f"    패턴: {', '.join(correct['patterns_found'])}")
                report.append("")
        
        # 추천사항
        if self.results['recommendations']:
            report.append("💡 추천사항:")
            for rec in self.results['recommendations']:
                report.append(f"  {rec}")
            report.append("")
        
        report.append("=" * 80)
        report.append("🎉 StockPilot UI 브랜딩 체크리스트 완료!")
        
        return "\n".join(report)


def main():
    """메인 실행 함수"""
    print("🚀 StockPilot AI UI 브랜딩 최종 확인 시작")
    
    try:
        checker = UIBrandingChecker()
        results = checker.run_branding_check()
        
        # 보고서 생성 및 저장
        report = checker.generate_report()
        
        # 콘솔 출력
        print("\n" + report)
        
        # JSON 파일로 상세 결과 저장
        with open('ui_branding_report.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # 텍스트 보고서 저장
        with open('ui_branding_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 상세 보고서 저장:")
        print(f"  - JSON: ui_branding_report.json")
        print(f"  - TEXT: ui_branding_report.txt")
        
        return results
        
    except Exception as e:
        print(f"❌ 브랜딩 체크 실행 실패: {e}")
        raise


if __name__ == "__main__":
    main()