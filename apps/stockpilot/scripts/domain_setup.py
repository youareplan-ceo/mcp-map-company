#!/usr/bin/env python3
"""
StockPilot AI 도메인 및 DNS 자동 설정 스크립트
작성자: StockPilot Team
용도: 도메인 등록, DNS 설정, 서브도메인 자동 생성
"""

import requests
import json
import os
import sys
import time
import dns.resolver
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DNSRecord:
    """DNS 레코드 데이터 클래스"""
    name: str
    type: str
    content: str
    ttl: int = 3600
    priority: Optional[int] = None

class DomainManager:
    """도메인 및 DNS 관리 클래스"""
    
    def __init__(self, provider: str = "cloudflare"):
        self.provider = provider
        self.api_key = None
        self.api_email = None
        self.zone_id = None
        self.domain = None
        
        self._load_credentials()
    
    def _load_credentials(self):
        """API 자격증명 로드"""
        if self.provider == "cloudflare":
            self.api_key = os.getenv('CLOUDFLARE_API_KEY')
            self.api_email = os.getenv('CLOUDFLARE_API_EMAIL')
        elif self.provider == "digitalocean":
            self.api_key = os.getenv('DIGITALOCEAN_API_TOKEN')
        elif self.provider == "namecheap":
            self.api_key = os.getenv('NAMECHEAP_API_KEY')
            self.api_user = os.getenv('NAMECHEAP_API_USER')
    
    def setup_cloudflare_dns(self, domain: str, server_ip: str) -> bool:
        """Cloudflare DNS 설정"""
        logger.info(f"Cloudflare DNS 설정 시작: {domain}")
        
        if not self.api_key or not self.api_email:
            logger.error("Cloudflare API 자격증명이 없습니다.")
            return False
        
        headers = {
            'X-Auth-Email': self.api_email,
            'X-Auth-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            # Zone ID 조회
            zones_url = "https://api.cloudflare.com/client/v4/zones"
            params = {'name': domain}
            response = requests.get(zones_url, headers=headers, params=params)
            zones = response.json()
            
            if not zones['success'] or not zones['result']:
                logger.error(f"도메인 {domain}을 찾을 수 없습니다.")
                return False
            
            self.zone_id = zones['result'][0]['id']
            logger.info(f"Zone ID: {self.zone_id}")
            
            # DNS 레코드들 설정
            dns_records = [
                DNSRecord("@", "A", server_ip),
                DNSRecord("www", "CNAME", domain),
                DNSRecord("api", "A", server_ip),
                DNSRecord("admin", "A", server_ip),
                DNSRecord("beta", "A", server_ip),
                # 메일 설정 (선택적)
                DNSRecord("@", "MX", "mail.stockpilot.ai", priority=10),
                DNSRecord("mail", "A", server_ip),
                # TXT 레코드 (보안)
                DNSRecord("@", "TXT", "v=spf1 include:_spf.google.com ~all"),
                DNSRecord("_dmarc", "TXT", "v=DMARC1; p=quarantine; rua=mailto:admin@stockpilot.ai")
            ]
            
            for record in dns_records:
                self._create_dns_record(record)
            
            logger.info("Cloudflare DNS 설정 완료")
            return True
            
        except Exception as e:
            logger.error(f"Cloudflare DNS 설정 실패: {e}")
            return False
    
    def _create_dns_record(self, record: DNSRecord) -> bool:
        """DNS 레코드 생성"""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records"
        
        headers = {
            'X-Auth-Email': self.api_email,
            'X-Auth-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'type': record.type,
            'name': record.name,
            'content': record.content,
            'ttl': record.ttl
        }
        
        if record.priority:
            data['priority'] = record.priority
        
        try:
            # 기존 레코드 확인
            existing_records = self._get_existing_records(record.name, record.type)
            
            if existing_records:
                # 기존 레코드 업데이트
                record_id = existing_records[0]['id']
                url = f"{url}/{record_id}"
                response = requests.put(url, headers=headers, json=data)
                action = "업데이트"
            else:
                # 새 레코드 생성
                response = requests.post(url, headers=headers, json=data)
                action = "생성"
            
            result = response.json()
            
            if result['success']:
                logger.info(f"DNS 레코드 {action} 성공: {record.name} {record.type} {record.content}")
                return True
            else:
                logger.error(f"DNS 레코드 {action} 실패: {result.get('errors', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"DNS 레코드 처리 실패: {e}")
            return False
    
    def _get_existing_records(self, name: str, record_type: str) -> List[Dict]:
        """기존 DNS 레코드 조회"""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records"
        
        headers = {
            'X-Auth-Email': self.api_email,
            'X-Auth-Key': self.api_key
        }
        
        params = {
            'name': f"{name}.{self.domain}" if name != "@" else self.domain,
            'type': record_type
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result['success']:
                return result['result']
            else:
                logger.warning(f"DNS 레코드 조회 실패: {result.get('errors', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"DNS 레코드 조회 오류: {e}")
            return []
    
    def verify_dns_propagation(self, domain: str, expected_ip: str) -> bool:
        """DNS 전파 확인"""
        logger.info(f"DNS 전파 확인 중: {domain} -> {expected_ip}")
        
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                # DNS 조회
                resolver = dns.resolver.Resolver()
                resolver.timeout = 10
                resolver.lifetime = 10
                
                answers = resolver.resolve(domain, 'A')
                
                for answer in answers:
                    if str(answer) == expected_ip:
                        logger.info(f"DNS 전파 완료: {domain} -> {expected_ip}")
                        return True
                
                logger.info(f"DNS 전파 대기 중... ({attempt + 1}/{max_attempts})")
                time.sleep(30)  # 30초 대기
                
            except Exception as e:
                logger.warning(f"DNS 조회 실패: {e}")
                time.sleep(30)
        
        logger.error(f"DNS 전파 타임아웃: {domain}")
        return False
    
    def setup_ssl_certificates(self, domain: str, email: str) -> bool:
        """SSL 인증서 자동 설정"""
        logger.info(f"SSL 인증서 설정 시작: {domain}")
        
        try:
            import subprocess
            
            # Let's Encrypt를 통한 SSL 인증서 발급
            cmd = [
                'sudo', 'certbot', 'certonly',
                '--nginx',
                '--non-interactive',
                '--agree-tos',
                '--email', email,
                '-d', domain,
                '-d', f'www.{domain}',
                '-d', f'api.{domain}',
                '-d', f'admin.{domain}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("SSL 인증서 발급 완료")
                
                # 자동 갱신 설정
                cron_job = "0 12 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx"
                subprocess.run(['crontab', '-l'], capture_output=True)
                subprocess.run(f'(crontab -l; echo "{cron_job}") | crontab -', 
                             shell=True, capture_output=True)
                
                logger.info("SSL 자동 갱신 설정 완료")
                return True
            else:
                logger.error(f"SSL 인증서 발급 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"SSL 설정 오류: {e}")
            return False
    
    def create_subdomains(self, base_domain: str, server_ip: str, subdomains: List[str]) -> bool:
        """서브도메인 자동 생성"""
        logger.info(f"서브도메인 생성 시작: {subdomains}")
        
        success_count = 0
        
        for subdomain in subdomains:
            record = DNSRecord(subdomain, "A", server_ip)
            if self._create_dns_record(record):
                success_count += 1
        
        logger.info(f"서브도메인 생성 완료: {success_count}/{len(subdomains)}")
        return success_count == len(subdomains)

class DomainSetupWizard:
    """도메인 설정 마법사"""
    
    def __init__(self):
        self.domain_manager = None
        self.domain = None
        self.server_ip = None
        self.email = None
    
    def run_interactive_setup(self):
        """대화형 설정 실행"""
        print("🌐 StockPilot AI 도메인 설정 마법사")
        print("=" * 50)
        
        # 기본 정보 입력
        self.domain = input("도메인명 입력 (예: stockpilot.ai): ").strip()
        self.server_ip = input("서버 IP 주소 입력: ").strip()
        self.email = input("관리자 이메일: ").strip()
        
        # DNS 제공자 선택
        print("\nDNS 제공자를 선택하세요:")
        print("1) Cloudflare (권장)")
        print("2) DigitalOcean")
        print("3) Namecheap")
        
        choice = input("선택 (1-3): ").strip()
        provider_map = {"1": "cloudflare", "2": "digitalocean", "3": "namecheap"}
        provider = provider_map.get(choice, "cloudflare")
        
        self.domain_manager = DomainManager(provider)
        
        # API 자격증명 입력
        self._setup_credentials(provider)
        
        # DNS 설정 실행
        if self._confirm_setup():
            self._execute_setup()
        else:
            print("설정이 취소되었습니다.")
    
    def _setup_credentials(self, provider: str):
        """API 자격증명 설정"""
        print(f"\n{provider.title()} API 자격증명을 입력하세요:")
        
        if provider == "cloudflare":
            api_key = input("Cloudflare API Key: ").strip()
            api_email = input("Cloudflare Email: ").strip()
            
            os.environ['CLOUDFLARE_API_KEY'] = api_key
            os.environ['CLOUDFLARE_API_EMAIL'] = api_email
            
        elif provider == "digitalocean":
            api_token = input("DigitalOcean API Token: ").strip()
            os.environ['DIGITALOCEAN_API_TOKEN'] = api_token
            
        elif provider == "namecheap":
            api_key = input("Namecheap API Key: ").strip()
            api_user = input("Namecheap API User: ").strip()
            
            os.environ['NAMECHEAP_API_KEY'] = api_key
            os.environ['NAMECHEAP_API_USER'] = api_user
        
        # 자격증명 다시 로드
        self.domain_manager._load_credentials()
    
    def _confirm_setup(self) -> bool:
        """설정 확인"""
        print("\n📋 설정 정보 확인:")
        print(f"- 도메인: {self.domain}")
        print(f"- 서버 IP: {self.server_ip}")
        print(f"- 이메일: {self.email}")
        print(f"- DNS 제공자: {self.domain_manager.provider}")
        
        confirm = input("\n계속 진행하시겠습니까? (y/N): ").strip().lower()
        return confirm in ['y', 'yes']
    
    def _execute_setup(self):
        """설정 실행"""
        print("\n🚀 도메인 설정을 시작합니다...")
        
        # 1. DNS 설정
        print("1. DNS 레코드 설정 중...")
        if self.domain_manager.provider == "cloudflare":
            success = self.domain_manager.setup_cloudflare_dns(self.domain, self.server_ip)
        else:
            print(f"{self.domain_manager.provider} DNS 설정은 아직 구현되지 않았습니다.")
            success = False
        
        if not success:
            print("❌ DNS 설정 실패")
            return
        
        # 2. 서브도메인 생성
        print("2. 서브도메인 생성 중...")
        subdomains = ['api', 'admin', 'beta', 'status', 'docs']
        self.domain_manager.create_subdomains(self.domain, self.server_ip, subdomains)
        
        # 3. DNS 전파 대기
        print("3. DNS 전파 확인 중...")
        if self.domain_manager.verify_dns_propagation(self.domain, self.server_ip):
            print("✅ DNS 전파 완료")
        else:
            print("⚠️ DNS 전파 미완료 (수동 확인 필요)")
        
        # 4. SSL 인증서 설정
        print("4. SSL 인증서 설정 중...")
        if self.domain_manager.setup_ssl_certificates(self.domain, self.email):
            print("✅ SSL 인증서 설정 완료")
        else:
            print("⚠️ SSL 인증서 설정 실패 (수동 설정 필요)")
        
        print("\n🎉 도메인 설정이 완료되었습니다!")
        print(f"🌐 웹사이트: https://{self.domain}")
        print(f"🔧 API: https://api.{self.domain}")
        print(f"👨‍💼 관리자: https://admin.{self.domain}")
        print(f"🧪 베타: https://beta.{self.domain}")

def create_nginx_ssl_config(domain: str) -> str:
    """SSL이 적용된 Nginx 설정 생성"""
    config = f"""
# StockPilot AI SSL 설정이 적용된 Nginx 설정
server {{
    listen 80;
    server_name {domain} www.{domain} api.{domain} admin.{domain} beta.{domain};
    
    # Let's Encrypt ACME Challenge
    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}
    
    # HTTPS로 리디렉트
    location / {{
        return 301 https://$server_name$request_uri;
    }}
}}

# 메인 도메인 (프론트엔드)
server {{
    listen 443 ssl http2;
    server_name {domain} www.{domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS 헤더
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # 프론트엔드 설정
    location / {{
        root /var/www/stockpilot/frontend/build;
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}

# API 서브도메인
server {{
    listen 443 ssl http2;
    server_name api.{domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}

# 관리자 서브도메인
server {{
    listen 443 ssl http2;
    server_name admin.{domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    # 관리자 페이지 접근 제한
    allow 127.0.0.1;
    # allow YOUR_IP;
    deny all;
    
    location / {{
        proxy_pass http://127.0.0.1:8001;  # 관리자 전용 포트
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}

# 베타 서브도메인
server {{
    listen 443 ssl http2;
    server_name beta.{domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    # 베타 사용자 인증
    auth_basic "Beta Access Required";
    auth_basic_user_file /etc/nginx/.htpasswd_beta;
    
    location / {{
        root /var/www/stockpilot/frontend/build;
        try_files $uri $uri/ /index.html;
    }}
}}
"""
    return config

def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # 대화형 모드
        wizard = DomainSetupWizard()
        wizard.run_interactive_setup()
    else:
        # 자동 모드 (환경 변수 사용)
        domain = os.getenv('DOMAIN', 'stockpilot.ai')
        server_ip = os.getenv('SERVER_IP', '127.0.0.1')
        email = os.getenv('EMAIL', 'admin@stockpilot.ai')
        
        domain_manager = DomainManager('cloudflare')
        
        print(f"🌐 자동 도메인 설정: {domain}")
        
        # DNS 설정
        if domain_manager.setup_cloudflare_dns(domain, server_ip):
            print("✅ DNS 설정 완료")
            
            # SSL 설정
            if domain_manager.setup_ssl_certificates(domain, email):
                print("✅ SSL 설정 완료")
            
            # Nginx 설정 생성
            nginx_config = create_nginx_ssl_config(domain)
            with open(f'/tmp/nginx_{domain}.conf', 'w') as f:
                f.write(nginx_config)
            print(f"📝 Nginx 설정 파일 생성: /tmp/nginx_{domain}.conf")
            
        else:
            print("❌ DNS 설정 실패")

if __name__ == "__main__":
    main()