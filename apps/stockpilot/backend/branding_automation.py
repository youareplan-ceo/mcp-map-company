#!/usr/bin/env python3
"""
유아플랜 공식 로고 적용 및 토스 스타일 브랜딩 자동화
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

class BrandingAutomation:
    def __init__(self):
        self.frontend_path = Path("/Users/youareplan/stockpilot-ai/frontend")
        self.brand_path = self.frontend_path / "public" / "brand"
        self.logo_url = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/HEAD/logo.png"
        
    async def download_youareplan_logo(self):
        """유아플랜 공식 로고 다운로드"""
        print("🎨 유아플랜 공식 로고 다운로드 중...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.logo_url) as response:
                    if response.status == 200:
                        logo_data = await response.read()
                        
                        # 브랜드 디렉토리 생성
                        self.brand_path.mkdir(parents=True, exist_ok=True)
                        
                        # 원본 로고 저장
                        with open(self.brand_path / "logo.png", "wb") as f:
                            f.write(logo_data)
                        
                        print("✅ 유아플랜 로고 다운로드 완료")
                        return True
                    else:
                        print(f"❌ 로고 다운로드 실패: HTTP {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 로고 다운로드 오류: {str(e)}")
            return False

    def create_favicon_variants(self):
        """파비콘 및 다양한 사이즈 아이콘 생성"""
        print("🎯 파비콘 및 아이콘 변형 생성 중...")
        
        logo_path = self.brand_path / "logo.png"
        if not logo_path.exists():
            print("❌ 원본 로고 파일이 존재하지 않습니다")
            return False
        
        try:
            with Image.open(logo_path) as logo:
                # 파비콘 (512x512)
                favicon = logo.resize((512, 512), Image.Resampling.LANCZOS)
                favicon.save(self.frontend_path / "public" / "favicon.png")
                
                # Apple touch icon (180x180)
                apple_icon = logo.resize((180, 180), Image.Resampling.LANCZOS)
                apple_icon.save(self.frontend_path / "public" / "apple-touch-icon.png")
                
                # PWA 아이콘들
                for size in [192, 512]:
                    pwa_icon = logo.resize((size, size), Image.Resampling.LANCZOS)
                    pwa_icon.save(self.frontend_path / "public" / f"icon-{size}x{size}.png")
                
                # OG 이미지 (1200x630)
                og_image = Image.new('RGB', (1200, 630), '#ffffff')
                
                # 로고를 중앙에 배치
                logo_size = min(400, int(630 * 0.6))
                logo_resized = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                x = (1200 - logo_size) // 2
                y = (630 - logo_size) // 2
                
                if logo_resized.mode == 'RGBA':
                    og_image.paste(logo_resized, (x, y), logo_resized)
                else:
                    og_image.paste(logo_resized, (x, y))
                
                og_image.save(self.frontend_path / "public" / "og-image.png")
                
                print("✅ 모든 아이콘 변형 생성 완료")
                return True
                
        except Exception as e:
            print(f"❌ 아이콘 생성 오류: {str(e)}")
            return False

    def update_html_meta_tags(self):
        """HTML 메타 태그 업데이트"""
        print("📝 HTML 메타 태그 업데이트 중...")
        
        index_path = self.frontend_path / "public" / "index.html"
        if not index_path.exists():
            print("❌ index.html 파일을 찾을 수 없습니다")
            return False
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 기존 메타 태그들을 더 완전한 것으로 교체
            updated_content = content
            
            # 파비콘 업데이트
            if '<link rel="icon"' not in content:
                updated_content = updated_content.replace(
                    '</head>',
                    '    <link rel="icon" type="image/png" href="/favicon.png">\n'
                    '    <link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
                    '</head>'
                )
            
            # OG 메타 태그 추가/업데이트
            og_tags = '''    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://stockpilot.youareplan.com">
    <meta property="og:title" content="StockPilot AI - AI 투자 코파일럿">
    <meta property="og:description" content="유아플랜이 개발한 AI 기반 한국 주식 투자 코파일럿 플랫폼">
    <meta property="og:image" content="/og-image.png">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://stockpilot.youareplan.com">
    <meta property="twitter:title" content="StockPilot AI - AI 투자 코파일럿">
    <meta property="twitter:description" content="유아플랜이 개발한 AI 기반 한국 주식 투자 코파일럿 플랫폼">
    <meta property="twitter:image" content="/og-image.png">

    <!-- PWA -->
    <link rel="manifest" href="/site.webmanifest">
    <meta name="theme-color" content="#2563eb">
'''
            
            if 'og:title' not in updated_content:
                updated_content = updated_content.replace('</head>', f'{og_tags}\n</head>')
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ HTML 메타 태그 업데이트 완료")
            return True
            
        except Exception as e:
            print(f"❌ HTML 업데이트 오류: {str(e)}")
            return False

    def create_webmanifest(self):
        """PWA manifest 생성"""
        print("📱 PWA manifest 생성 중...")
        
        manifest = {
            "name": "StockPilot AI",
            "short_name": "StockPilot",
            "description": "유아플랜이 개발한 AI 기반 한국 주식 투자 코파일럿 플랫폼",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#2563eb",
            "icons": [
                {
                    "src": "/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
        
        try:
            manifest_path = self.frontend_path / "public" / "site.webmanifest"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print("✅ PWA manifest 생성 완료")
            return True
            
        except Exception as e:
            print(f"❌ Manifest 생성 오류: {str(e)}")
            return False

    def update_brand_tokens(self):
        """브랜드 토큰 파일 업데이트"""
        print("🎨 브랜드 토큰 업데이트 중...")
        
        try:
            # 브랜드 토큰 디렉토리 생성
            theme_path = self.frontend_path / "src" / "styles"
            theme_path.mkdir(parents=True, exist_ok=True)
            
            # 브랜드 토큰 파일 생성
            brand_tokens = """/**
 * 유아플랜 브랜드 토큰 - 토스 스타일 모바일 최적화
 */

export const BRAND_TOKENS = {
  // 로고 및 이미지
  logo: {
    path: '/brand/logo.png',
    alt: 'YouArePlan StockPilot AI'
  },
  
  // 파비콘 및 아이콘
  icons: {
    favicon: '/favicon.png',
    appleTouchIcon: '/apple-touch-icon.png',
    ogImage: '/og-image.png'
  },
  
  // 컬러 시스템 (토스 스타일)
  colors: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe', 
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      900: '#1e3a8a'
    },
    gray: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      500: '#6b7280',
      700: '#374151',
      900: '#111827'
    },
    background: '#ffffff',
    surface: '#f9fafb'
  },
  
  // 타이포그래피 (모바일 최적화)
  typography: {
    fontFamily: {
      sans: ['Pretendard', 'system-ui', '-apple-system', 'sans-serif']
    },
    fontSize: {
      xs: '12px',
      sm: '14px', 
      base: '16px',
      lg: '18px',
      xl: '20px',
      '2xl': '24px',
      '3xl': '30px'
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    }
  },
  
  // 스페이싱 (토스 스타일)
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px'
  },
  
  // 보더 반경
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px'
  },
  
  // 그림자 (토스 스타일)
  shadow: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    card: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -1px rgb(0 0 0 / 0.06)'
  },
  
  // 애니메이션
  transition: {
    default: '0.15s ease',
    fast: '0.1s ease',
    slow: '0.3s ease'
  }
};

export default BRAND_TOKENS;
"""
            
            with open(theme_path / "brand.js", 'w', encoding='utf-8') as f:
                f.write(brand_tokens)
            
            print("✅ 브랜드 토큰 업데이트 완료")
            return True
            
        except Exception as e:
            print(f"❌ 브랜드 토큰 업데이트 오류: {str(e)}")
            return False

    async def run_branding_automation(self):
        """브랜딩 자동화 전체 실행"""
        print("🚀 유아플랜 공식 로고 적용 시작")
        print("="*60)
        
        # 1. 로고 다운로드
        if not await self.download_youareplan_logo():
            return False
        
        # 2. 아이콘 변형 생성
        if not self.create_favicon_variants():
            return False
        
        # 3. HTML 메타 태그 업데이트
        if not self.update_html_meta_tags():
            return False
        
        # 4. PWA manifest 생성
        if not self.create_webmanifest():
            return False
        
        # 5. 브랜드 토큰 업데이트
        if not self.update_brand_tokens():
            return False
        
        print("="*60)
        print("✅ 유아플랜 공식 로고 적용 완료!")
        return True

async def main():
    automation = BrandingAutomation()
    success = await automation.run_branding_automation()
    
    if success:
        print("\n🎉 브랜딩 자동화 성공!")
        print("📝 생성된 파일들:")
        print("   - /public/brand/logo.png")
        print("   - /public/favicon.png")
        print("   - /public/apple-touch-icon.png")
        print("   - /public/og-image.png")
        print("   - /public/icon-192x192.png")
        print("   - /public/icon-512x512.png")
        print("   - /public/site.webmanifest")
        print("   - /src/styles/brand.js")
        print("   - /public/index.html (메타 태그 업데이트)")
    else:
        print("\n❌ 브랜딩 자동화 실패")

if __name__ == "__main__":
    asyncio.run(main())