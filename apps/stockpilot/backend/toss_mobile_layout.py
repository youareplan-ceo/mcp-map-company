#!/usr/bin/env python3
"""
토스 스타일 모바일 레이아웃 고도화 자동화
"""

import json
import os
from pathlib import Path
from datetime import datetime

class TossMobileLayoutEnhancer:
    def __init__(self):
        self.frontend_path = Path("/Users/youareplan/stockpilot-ai/frontend")
        self.src_path = self.frontend_path / "src"
        self.components_path = self.src_path / "components"
        self.styles_path = self.src_path / "styles"
        
    def create_toss_global_styles(self):
        """토스 스타일 글로벌 CSS 생성"""
        print("🎨 토스 스타일 글로벌 CSS 생성 중...")
        
        global_css = """/* 토스 스타일 글로벌 CSS - 모바일 최적화 */

/* 폰트 및 기본 설정 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f9fafb;
  color: #111827;
  line-height: 1.5;
  font-size: 16px;
}

/* 토스 스타일 컨테이너 */
.toss-container {
  max-width: 428px;
  margin: 0 auto;
  padding: 0 16px;
  background: #ffffff;
  min-height: 100vh;
}

/* 토스 스타일 카드 */
.toss-card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  margin: 16px 0;
  overflow: hidden;
  transition: all 0.15s ease;
}

.toss-card:active {
  transform: scale(0.98);
  box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.15);
}

.toss-card-header {
  padding: 20px 20px 0 20px;
  border-bottom: none;
}

.toss-card-body {
  padding: 20px;
}

.toss-card-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
}

.toss-card-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 16px;
}

/* 토스 스타일 버튼 */
.toss-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 16px 24px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
  width: 100%;
  margin: 8px 0;
}

.toss-btn-primary {
  background: #2563eb;
  color: #ffffff;
}

.toss-btn-primary:hover {
  background: #1d4ed8;
}

.toss-btn-primary:active {
  background: #1e40af;
  transform: scale(0.98);
}

.toss-btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.toss-btn-secondary:hover {
  background: #e5e7eb;
}

.toss-btn-outline {
  background: transparent;
  color: #2563eb;
  border: 1px solid #e5e7eb;
}

/* 토스 스타일 입력 필드 */
.toss-input {
  width: 100%;
  padding: 16px 20px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-size: 16px;
  color: #111827;
  background: #ffffff;
  transition: all 0.15s ease;
  margin: 8px 0;
}

.toss-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 0.1);
}

.toss-input::placeholder {
  color: #9ca3af;
}

/* 토스 스타일 네비게이션 */
.toss-nav {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 16px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.toss-nav-title {
  font-size: 18px;
  font-weight: 600;
  text-align: center;
  color: #111827;
}

/* 토스 스타일 리스트 */
.toss-list {
  background: #ffffff;
  border-radius: 12px;
  margin: 16px 0;
  overflow: hidden;
}

.toss-list-item {
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.15s ease;
}

.toss-list-item:last-child {
  border-bottom: none;
}

.toss-list-item:active {
  background: #f9fafb;
}

.toss-list-item-content {
  flex: 1;
}

.toss-list-item-title {
  font-size: 16px;
  font-weight: 500;
  color: #111827;
  margin-bottom: 4px;
}

.toss-list-item-subtitle {
  font-size: 14px;
  color: #6b7280;
}

.toss-list-item-value {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

/* 토스 스타일 태그/배지 */
.toss-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.toss-badge-success {
  background: #dcfce7;
  color: #166534;
}

.toss-badge-warning {
  background: #fef3c7;
  color: #92400e;
}

.toss-badge-error {
  background: #fecaca;
  color: #991b1b;
}

.toss-badge-info {
  background: #dbeafe;
  color: #1e40af;
}

/* 토스 스타일 차트 카드 */
.toss-chart-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  border-radius: 16px;
  padding: 24px;
  margin: 16px 0;
  position: relative;
  overflow: hidden;
}

.toss-chart-value {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.toss-chart-label {
  font-size: 14px;
  opacity: 0.8;
  margin-bottom: 16px;
}

.toss-chart-change {
  display: inline-flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.2);
}

/* 반응형 디자인 */
@media (max-width: 428px) {
  .toss-container {
    padding: 0 12px;
  }
  
  .toss-card {
    margin: 12px 0;
  }
  
  .toss-card-body {
    padding: 16px;
  }
  
  .toss-btn {
    padding: 14px 20px;
  }
}

/* 다크 모드 지원 */
@media (prefers-color-scheme: dark) {
  body {
    background-color: #111827;
    color: #f9fafb;
  }
  
  .toss-container {
    background: #1f2937;
  }
  
  .toss-card {
    background: #1f2937;
    border: 1px solid #374151;
  }
  
  .toss-card-title {
    color: #f9fafb;
  }
  
  .toss-input {
    background: #374151;
    border-color: #4b5563;
    color: #f9fafb;
  }
  
  .toss-nav {
    background: #1f2937;
    border-color: #374151;
  }
  
  .toss-list {
    background: #1f2937;
    border: 1px solid #374151;
  }
  
  .toss-list-item {
    border-color: #374151;
  }
  
  .toss-list-item:active {
    background: #374151;
  }
}

/* 애니메이션 */
@keyframes toss-slide-up {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.toss-animate-slide-up {
  animation: toss-slide-up 0.3s ease;
}

@keyframes toss-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.toss-animate-fade-in {
  animation: toss-fade-in 0.3s ease;
}

/* 로딩 스피너 */
.toss-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 토스 스타일 하단 네비게이션 */
.toss-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 428px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-around;
  padding: 12px 0 max(12px, env(safe-area-inset-bottom));
  z-index: 1000;
}

.toss-bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  text-decoration: none;
  color: #6b7280;
}

.toss-bottom-nav-item.active {
  color: #2563eb;
}

.toss-bottom-nav-icon {
  width: 24px;
  height: 24px;
  margin-bottom: 4px;
}

.toss-bottom-nav-label {
  font-size: 10px;
  font-weight: 500;
}
"""
        
        try:
            # 스타일 디렉토리 생성
            self.styles_path.mkdir(parents=True, exist_ok=True)
            
            # 글로벌 CSS 파일 생성
            with open(self.styles_path / "toss-mobile.css", 'w', encoding='utf-8') as f:
                f.write(global_css)
            
            print("✅ 토스 스타일 글로벌 CSS 생성 완료")
            return True
            
        except Exception as e:
            print(f"❌ 글로벌 CSS 생성 오류: {str(e)}")
            return False

    def create_enhanced_components(self):
        """토스 스타일 강화 컴포넌트 생성"""
        print("🔧 토스 스타일 컴포넌트 강화 중...")
        
        # 토스 스타일 카드 컴포넌트
        toss_card_component = """import React from 'react';
import './TossCard.css';

interface TossCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  gradient?: boolean;
}

const TossCard: React.FC<TossCardProps> = ({ 
  children, 
  className = '', 
  onClick,
  gradient = false 
}) => {
  return (
    <div 
      className={`toss-card ${gradient ? 'toss-chart-card' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

export default TossCard;
"""
        
        # 토스 스타일 버튼 컴포넌트
        toss_button_component = """import React from 'react';
import './TossButton.css';

interface TossButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

const TossButton: React.FC<TossButtonProps> = ({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  onClick,
  className = '',
  type = 'button'
}) => {
  return (
    <button
      type={type}
      className={`toss-btn toss-btn-${variant} toss-btn-${size} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <div className="toss-spinner" />}
      {!loading && children}
    </button>
  );
};

export default TossButton;
"""

        # 토스 스타일 리스트 컴포넌트
        toss_list_component = """import React from 'react';
import './TossList.css';

interface TossListItemProps {
  title: string;
  subtitle?: string;
  value?: string | number;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'error' | 'info';
  };
  onClick?: () => void;
}

interface TossListProps {
  items: TossListItemProps[];
  className?: string;
}

const TossList: React.FC<TossListProps> = ({ items, className = '' }) => {
  return (
    <div className={`toss-list ${className}`}>
      {items.map((item, index) => (
        <div 
          key={index}
          className="toss-list-item"
          onClick={item.onClick}
        >
          <div className="toss-list-item-content">
            <div className="toss-list-item-title">{item.title}</div>
            {item.subtitle && (
              <div className="toss-list-item-subtitle">{item.subtitle}</div>
            )}
          </div>
          <div className="toss-list-item-right">
            {item.value && (
              <div className="toss-list-item-value">{item.value}</div>
            )}
            {item.badge && (
              <span className={`toss-badge toss-badge-${item.badge.variant}`}>
                {item.badge.text}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TossList;
"""

        try:
            # 컴포넌트 디렉토리 생성
            toss_components_path = self.components_path / "toss"
            toss_components_path.mkdir(parents=True, exist_ok=True)
            
            # 컴포넌트 파일들 생성
            with open(toss_components_path / "TossCard.tsx", 'w', encoding='utf-8') as f:
                f.write(toss_card_component)
            
            with open(toss_components_path / "TossButton.tsx", 'w', encoding='utf-8') as f:
                f.write(toss_button_component)
                
            with open(toss_components_path / "TossList.tsx", 'w', encoding='utf-8') as f:
                f.write(toss_list_component)
            
            print("✅ 토스 스타일 컴포넌트 강화 완료")
            return True
            
        except Exception as e:
            print(f"❌ 컴포넌트 강화 오류: {str(e)}")
            return False

    def update_main_app_css(self):
        """메인 App.css 업데이트"""
        print("📱 메인 App.css 토스 스타일 업데이트 중...")
        
        app_css_path = self.src_path / "App.css"
        if not app_css_path.exists():
            print("❌ App.css 파일을 찾을 수 없습니다")
            return False
        
        try:
            # 토스 스타일 임포트 추가
            toss_import = """@import './styles/toss-mobile.css';

"""
            
            with open(app_css_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 토스 스타일 임포트가 없으면 추가
            if '@import \'./styles/toss-mobile.css\'' not in content:
                updated_content = toss_import + content
                
                with open(app_css_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
            
            print("✅ App.css 토스 스타일 업데이트 완료")
            return True
            
        except Exception as e:
            print(f"❌ App.css 업데이트 오류: {str(e)}")
            return False

    def create_mobile_responsive_config(self):
        """모바일 반응형 설정 생성"""
        print("📱 모바일 반응형 설정 생성 중...")
        
        responsive_config = {
            "breakpoints": {
                "mobile": "428px",
                "tablet": "768px",
                "desktop": "1024px"
            },
            "mobile_first": True,
            "toss_container_width": "428px",
            "safe_area_insets": True,
            "touch_optimized": True,
            "font_scaling": {
                "base": "16px",
                "mobile": "16px",
                "large_text": "18px"
            },
            "spacing": {
                "xs": "4px",
                "sm": "8px", 
                "md": "16px",
                "lg": "24px",
                "xl": "32px"
            },
            "animations": {
                "duration": "0.15s",
                "easing": "ease",
                "scale_press": "0.98"
            }
        }
        
        try:
            with open(self.styles_path / "responsive-config.json", 'w', encoding='utf-8') as f:
                json.dump(responsive_config, f, ensure_ascii=False, indent=2)
            
            print("✅ 모바일 반응형 설정 생성 완료")
            return True
            
        except Exception as e:
            print(f"❌ 반응형 설정 생성 오류: {str(e)}")
            return False

    async def run_mobile_layout_enhancement(self):
        """토스 스타일 모바일 레이아웃 고도화 전체 실행"""
        print("🚀 토스 스타일 모바일 레이아웃 고도화 시작")
        print("="*60)
        
        # 1. 글로벌 CSS 생성
        if not self.create_toss_global_styles():
            return False
        
        # 2. 컴포넌트 강화
        if not self.create_enhanced_components():
            return False
        
        # 3. App.css 업데이트
        if not self.update_main_app_css():
            return False
        
        # 4. 반응형 설정 생성
        if not self.create_mobile_responsive_config():
            return False
        
        print("="*60)
        print("✅ 토스 스타일 모바일 레이아웃 고도화 완료!")
        return True

async def main():
    enhancer = TossMobileLayoutEnhancer()
    success = await enhancer.run_mobile_layout_enhancement()
    
    if success:
        print("\n🎉 토스 스타일 모바일 레이아웃 고도화 성공!")
        print("📝 생성된 파일들:")
        print("   - /src/styles/toss-mobile.css")
        print("   - /src/styles/responsive-config.json")
        print("   - /src/components/toss/TossCard.tsx")
        print("   - /src/components/toss/TossButton.tsx")
        print("   - /src/components/toss/TossList.tsx")
        print("   - /src/App.css (업데이트됨)")
        print("\n📱 모바일 최적화 특징:")
        print("   ✅ 428px 중심의 토스 스타일 컨테이너")
        print("   ✅ 터치 최적화된 버튼 및 인터랙션")
        print("   ✅ 카드 기반 미니멀 디자인")
        print("   ✅ 다크모드 지원")
        print("   ✅ 부드러운 애니메이션")
        print("   ✅ Safe Area 지원")
    else:
        print("\n❌ 토스 스타일 모바일 레이아웃 고도화 실패")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())