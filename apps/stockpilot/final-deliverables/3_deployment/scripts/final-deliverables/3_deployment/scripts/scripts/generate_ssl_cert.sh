#!/bin/bash
# SSL/TLS 자체 서명 인증서 생성 스크립트
# 프로덕션 환경에서는 Let's Encrypt 또는 상용 인증서 사용 권장

set -e

SSL_DIR="/Users/youareplan/stockpilot-ai/nginx/ssl"
DOMAIN="stockpilot.ai"

echo "🔐 SSL/TLS 인증서 생성 중..."

# SSL 디렉토리 생성
mkdir -p "$SSL_DIR"

# 개인키 생성
openssl genrsa -out "$SSL_DIR/$DOMAIN.key" 4096

# CSR (Certificate Signing Request) 생성
openssl req -new -key "$SSL_DIR/$DOMAIN.key" -out "$SSL_DIR/$DOMAIN.csr" -subj "/C=KR/ST=Seoul/L=Seoul/O=StockPilot/OU=IT Department/CN=$DOMAIN/emailAddress=admin@$DOMAIN"

# 자체 서명 인증서 생성 (365일 유효)
openssl x509 -req -days 365 -in "$SSL_DIR/$DOMAIN.csr" -signkey "$SSL_DIR/$DOMAIN.key" -out "$SSL_DIR/$DOMAIN.crt"

# 권한 설정
chmod 600 "$SSL_DIR/$DOMAIN.key"
chmod 644 "$SSL_DIR/$DOMAIN.crt"

echo "✅ SSL 인증서 생성 완료!"
echo "📁 위치: $SSL_DIR"
echo "🔑 Private Key: $DOMAIN.key"
echo "📜 Certificate: $DOMAIN.crt"
echo ""
echo "⚠️  주의: 이것은 자체 서명 인증서입니다."
echo "   프로덕션 환경에서는 Let's Encrypt 또는 상용 인증서를 사용하세요."
echo ""
echo "📋 Let's Encrypt 사용법:"
echo "   certbot --nginx -d $DOMAIN -d www.$DOMAIN"