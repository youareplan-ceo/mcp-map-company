#!/usr/bin/env python3
"""
Locust 기반 부하 테스트 스크립트
/api/v1/portfolio 와 /api/v1/recommend API 테스트
"""

import os
import random
import time
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import gevent


class MCPMapAPIUser(HttpUser):
    """MCP Map Company API 부하 테스트 사용자"""

    wait_time = between(1, 3)  # 1~3초 랜덤 지연

    def on_start(self):
        """테스트 시작 시 인증 설정"""
        self.api_key = os.getenv('MCP_API_KEY', 'test-api-key-12345')
        self.jwt_token = os.getenv('JWT_TOKEN', 'test-jwt-token')

        self.client.headers.update({
            'X-API-KEY': self.api_key,
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    @task(3)
    def test_portfolio_api(self):
        """포트폴리오 API 테스트 (가중치 3)"""
        with self.client.get(
            "/api/v1/portfolio",
            catch_response=True,
            name="portfolio_get"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'totalValue' in data or 'holdings' in data:
                        response.success()
                    else:
                        response.failure("응답 데이터 형식 오류")
                except Exception as e:
                    response.failure(f"JSON 파싱 오류: {str(e)}")
            elif response.status_code == 401:
                response.failure("인증 실패")
            elif response.status_code == 404:
                response.failure("API 엔드포인트 없음")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def test_recommend_api(self):
        """추천 API 테스트 (가중치 2)"""
        with self.client.get(
            "/api/v1/recommend",
            catch_response=True,
            name="recommend_get"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'recommendations' in data or 'signals' in data:
                        response.success()
                    else:
                        response.failure("응답 데이터 형식 오류")
                except Exception as e:
                    response.failure(f"JSON 파싱 오류: {str(e)}")
            elif response.status_code == 401:
                response.failure("인증 실패")
            elif response.status_code == 404:
                response.failure("API 엔드포인트 없음")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def test_health_check(self):
        """헬스체크 API 테스트 (가중치 1)"""
        with self.client.get(
            "/health",
            catch_response=True,
            name="health_check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


def run_load_test(
    host="https://mcp-map-company.onrender.com",
    users=100,
    spawn_rate=10,
    run_time="5m",
    html_report_path="reports/load_test/load_test_report.html"
):
    """부하 테스트 실행 함수"""

    # 리포트 디렉토리 생성
    os.makedirs(os.path.dirname(html_report_path), exist_ok=True)

    # Locust 환경 설정
    setup_logging("INFO", None)

    env = Environment(user_classes=[MCPMapAPIUser])
    env.create_local_runner()

    # 통계 로깅 시작
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)

    print(f"🚀 부하 테스트 시작")
    print(f"   대상: {host}")
    print(f"   사용자: {users}명")
    print(f"   실행 시간: {run_time}")
    print(f"   리포트: {html_report_path}")
    print("-" * 50)

    # 테스트 시작
    env.runner.start(users, spawn_rate=spawn_rate)

    # 실행 시간 파싱 및 대기
    if run_time.endswith('m'):
        wait_seconds = int(run_time[:-1]) * 60
    elif run_time.endswith('s'):
        wait_seconds = int(run_time[:-1])
    else:
        wait_seconds = 300  # 기본 5분

    gevent.sleep(wait_seconds)

    # 테스트 중지
    env.runner.stop()

    # HTML 리포트 생성
    stats = env.runner.stats

    html_content = generate_html_report(stats, host, users, run_time)

    with open(html_report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ 테스트 완료!")
    print(f"📊 리포트 저장: {html_report_path}")

    # 요약 통계 출력
    print("\n📈 테스트 결과 요약:")
    print(f"   총 요청: {stats.total.num_requests}")
    print(f"   실패: {stats.total.num_failures}")
    print(f"   평균 응답시간: {stats.total.avg_response_time:.2f}ms")
    print(f"   RPS: {stats.total.current_rps:.2f}")

    return stats


def generate_html_report(stats, host, users, run_time):
    """HTML 리포트 생성"""

    # 통계 데이터 수집
    total_stats = stats.total
    entries = []

    for name, entry in stats.entries.items():
        if name != "Aggregated":
            entries.append({
                'name': name,
                'requests': entry.num_requests,
                'failures': entry.num_failures,
                'avg_time': entry.avg_response_time,
                'min_time': entry.min_response_time,
                'max_time': entry.max_response_time,
                'rps': entry.current_rps
            })

    # HTML 템플릿
    html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Map 부하 테스트 리포트</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2563eb; }}
        .metric-label {{ color: #6b7280; font-size: 0.9em; margin-top: 5px; }}
        table {{ width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        .success {{ color: #059669; }}
        .error {{ color: #dc2626; }}
        .timestamp {{ color: #6b7280; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 MCP Map 부하 테스트 리포트</h1>
            <p><strong>대상 서버:</strong> {host}</p>
            <p><strong>테스트 시간:</strong> {run_time} | <strong>동시 사용자:</strong> {users}명</p>
            <p class="timestamp">생성 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="summary">
            <div class="metric">
                <div class="metric-value">{total_stats.num_requests:,}</div>
                <div class="metric-label">총 요청</div>
            </div>
            <div class="metric">
                <div class="metric-value {'success' if total_stats.num_failures == 0 else 'error'}">{total_stats.num_failures:,}</div>
                <div class="metric-label">실패</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_stats.avg_response_time:.0f}ms</div>
                <div class="metric-label">평균 응답시간</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_stats.current_rps:.1f}</div>
                <div class="metric-label">RPS</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>API 엔드포인트</th>
                    <th>요청 수</th>
                    <th>실패</th>
                    <th>평균 (ms)</th>
                    <th>최소 (ms)</th>
                    <th>최대 (ms)</th>
                    <th>RPS</th>
                </tr>
            </thead>
            <tbody>
"""

    # 엔트리별 통계 추가
    for entry in entries:
        html_template += f"""
                <tr>
                    <td><code>{entry['name']}</code></td>
                    <td>{entry['requests']:,}</td>
                    <td class="{'error' if entry['failures'] > 0 else 'success'}">{entry['failures']:,}</td>
                    <td>{entry['avg_time']:.0f}</td>
                    <td>{entry['min_time']:.0f}</td>
                    <td>{entry['max_time']:.0f}</td>
                    <td>{entry['rps']:.1f}</td>
                </tr>
"""

    html_template += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    return html_template


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MCP Map API 부하 테스트')
    parser.add_argument('--host', default='https://mcp-map-company.onrender.com', help='테스트 대상 호스트')
    parser.add_argument('--users', type=int, default=100, help='동시 사용자 수')
    parser.add_argument('--spawn-rate', type=int, default=10, help='사용자 생성 속도')
    parser.add_argument('--time', default='5m', help='실행 시간 (예: 5m, 300s)')
    parser.add_argument('--output', default='reports/load_test/load_test_report.html', help='리포트 출력 경로')

    args = parser.parse_args()

    run_load_test(
        host=args.host,
        users=args.users,
        spawn_rate=args.spawn_rate,
        run_time=args.time,
        html_report_path=args.output
    )