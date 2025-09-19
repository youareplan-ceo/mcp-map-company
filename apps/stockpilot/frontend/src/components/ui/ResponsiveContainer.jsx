import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

// 반응형 브레이크포인트 정의
const breakpoints = {
  mobile: '320px',
  mobileLarge: '425px', 
  tablet: '768px',
  laptop: '1024px',
  desktop: '1200px',
  desktopLarge: '1440px',
};

// 미디어 쿼리 헬퍼
export const media = {
  mobile: `@media screen and (max-width: ${breakpoints.mobileLarge})`,
  tablet: `@media screen and (min-width: ${breakpoints.mobileLarge}) and (max-width: ${breakpoints.laptop})`,
  laptop: `@media screen and (min-width: ${breakpoints.laptop}) and (max-width: ${breakpoints.desktop})`,
  desktop: `@media screen and (min-width: ${breakpoints.desktop})`,
  
  // 특정 범위
  mobileOnly: `@media screen and (max-width: ${breakpoints.tablet})`,
  tabletUp: `@media screen and (min-width: ${breakpoints.tablet})`,
  laptopUp: `@media screen and (min-width: ${breakpoints.laptop})`,
  desktopUp: `@media screen and (min-width: ${breakpoints.desktop})`,
  
  // 터치 디바이스
  touch: '@media (hover: none) and (pointer: coarse)',
  hover: '@media (hover: hover) and (pointer: fine)',
  
  // 화면 방향
  portrait: '@media (orientation: portrait)',
  landscape: '@media (orientation: landscape)',
  
  // 고해상도 디스플레이
  retina: '@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi)',
};

// 반응형 컨테이너
const Container = styled.div`
  width: 100%;
  margin: 0 auto;
  padding: 0 16px;
  
  /* 모바일 */
  ${media.mobile} {
    padding: 0 12px;
    max-width: 100%;
  }
  
  /* 태블릿 */
  ${media.tablet} {
    padding: 0 20px;
    max-width: 768px;
  }
  
  /* 랩톱 */
  ${media.laptop} {
    padding: 0 24px;
    max-width: 1024px;
  }
  
  /* 데스크톱 */
  ${media.desktop} {
    padding: 0 32px;
    max-width: 1200px;
  }
  
  /* 대형 데스크톱 */
  @media screen and (min-width: ${breakpoints.desktopLarge}) {
    padding: 0 40px;
    max-width: 1400px;
  }
`;

// 그리드 시스템
const Grid = styled.div`
  display: grid;
  gap: ${props => props.gap || '16px'};
  grid-template-columns: ${props => props.columns || 'repeat(auto-fit, minmax(300px, 1fr))'};
  
  ${media.mobile} {
    gap: 12px;
    grid-template-columns: 1fr;
  }
  
  ${media.tablet} {
    gap: 16px;
    grid-template-columns: ${props => props.tabletColumns || 'repeat(auto-fit, minmax(250px, 1fr))'};
  }
  
  ${media.laptop} {
    gap: 20px;
    grid-template-columns: ${props => props.laptopColumns || props.columns || 'repeat(auto-fit, minmax(300px, 1fr))'};
  }
  
  ${media.desktop} {
    gap: 24px;
    grid-template-columns: ${props => props.desktopColumns || props.columns || 'repeat(auto-fit, minmax(350px, 1fr))'};
  }
`;

// 플렉스 컨테이너
const Flex = styled.div`
  display: flex;
  flex-direction: ${props => props.direction || 'row'};
  justify-content: ${props => props.justify || 'flex-start'};
  align-items: ${props => props.align || 'stretch'};
  gap: ${props => props.gap || '16px'};
  flex-wrap: ${props => props.wrap || 'nowrap'};
  
  ${media.mobile} {
    flex-direction: ${props => props.mobileDirection || 'column'};
    gap: ${props => props.mobileGap || '12px'};
    flex-wrap: wrap;
  }
  
  ${media.tablet} {
    flex-direction: ${props => props.tabletDirection || props.direction || 'row'};
    gap: ${props => props.tabletGap || '16px'};
  }
`;

// 반응형 텍스트
const ResponsiveText = styled.div`
  font-size: ${props => props.size || '16px'};
  line-height: ${props => props.lineHeight || '1.5'};
  
  ${media.mobile} {
    font-size: ${props => props.mobileSize || 'calc(' + (props.size || '16px') + ' * 0.875)'};
    line-height: ${props => props.mobileLineHeight || '1.4'};
  }
  
  ${media.tablet} {
    font-size: ${props => props.tabletSize || props.size || '16px'};
  }
  
  ${media.desktop} {
    font-size: ${props => props.desktopSize || props.size || '16px'};
  }
`;

// 반응형 간격
const Spacer = styled.div`
  height: ${props => props.height || '24px'};
  width: ${props => props.width || 'auto'};
  
  ${media.mobile} {
    height: ${props => props.mobileHeight || 'calc(' + (props.height || '24px') + ' * 0.75)'};
    width: ${props => props.mobileWidth || props.width || 'auto'};
  }
  
  ${media.tablet} {
    height: ${props => props.tabletHeight || props.height || '24px'};
    width: ${props => props.tabletWidth || props.width || 'auto'};
  }
`;

// 반응형 카드
const ResponsiveCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }
  
  ${media.mobile} {
    padding: 16px;
    border-radius: 8px;
    
    &:hover {
      transform: none; /* 모바일에서는 호버 효과 제거 */
    }
  }
  
  ${media.tablet} {
    padding: 20px;
    border-radius: 10px;
  }
  
  ${media.desktop} {
    padding: 28px;
    border-radius: 16px;
  }
`;

// 반응형 버튼
const ResponsiveButton = styled.button`
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 44px; /* 터치 친화적 최소 높이 */
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  ${media.mobile} {
    width: 100%;
    padding: 14px 20px;
    font-size: 16px;
    min-height: 48px;
    
    &:hover {
      transform: none;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
  }
  
  ${media.tablet} {
    padding: 12px 28px;
    font-size: 15px;
  }
  
  ${media.desktop} {
    padding: 14px 32px;
    font-size: 16px;
  }
  
  ${media.touch} {
    min-height: 48px;
    padding: 14px 24px;
  }
`;

// 디바이스 타입 감지 훅
export const useDeviceType = () => {
  const [deviceType, setDeviceType] = useState('desktop');
  const [screenSize, setScreenSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  });

  useEffect(() => {
    const updateDeviceType = () => {
      const width = window.innerWidth;
      setScreenSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });

      if (width <= 425) {
        setDeviceType('mobile');
      } else if (width <= 768) {
        setDeviceType('tablet');
      } else if (width <= 1024) {
        setDeviceType('laptop');
      } else {
        setDeviceType('desktop');
      }
    };

    updateDeviceType();
    window.addEventListener('resize', updateDeviceType);
    return () => window.removeEventListener('resize', updateDeviceType);
  }, []);

  return {
    deviceType,
    screenSize,
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isLaptop: deviceType === 'laptop',
    isDesktop: deviceType === 'desktop',
    isTouchDevice: 'ontouchstart' in window,
  };
};

// 터치 친화적 입력 컴포넌트
const ResponsiveInput = styled.input`
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: white;
  transition: all 0.3s ease;
  min-height: 44px;
  
  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
  
  ${media.mobile} {
    font-size: 16px; /* iOS 줌 방지를 위해 16px 이상 유지 */
    padding: 14px 16px;
    min-height: 48px;
  }
  
  ${media.touch} {
    min-height: 48px;
    padding: 14px 16px;
  }
`;

// 반응형 네비게이션
const ResponsiveNav = styled.nav`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  
  ${media.mobile} {
    padding: 12px 16px;
    flex-wrap: wrap;
    
    .nav-menu {
      width: 100%;
      order: 3;
      margin-top: 12px;
      display: ${props => props.mobileMenuOpen ? 'flex' : 'none'};
      flex-direction: column;
      gap: 8px;
    }
    
    .nav-toggle {
      display: block;
    }
  }
  
  ${media.tabletUp} {
    .nav-menu {
      display: flex !important;
      align-items: center;
      gap: 24px;
    }
    
    .nav-toggle {
      display: none;
    }
  }
`;

// 햄버거 메뉴 버튼
const HamburgerButton = styled.button`
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 3px;
  
  span {
    width: 20px;
    height: 2px;
    background: #374151;
    transition: all 0.3s ease;
    border-radius: 1px;
  }
  
  ${props => props.isOpen && `
    span:nth-child(1) {
      transform: rotate(45deg) translate(5px, 5px);
    }
    
    span:nth-child(2) {
      opacity: 0;
    }
    
    span:nth-child(3) {
      transform: rotate(-45deg) translate(7px, -6px);
    }
  `}
  
  ${media.mobile} {
    display: flex;
  }
`;

// 반응형 컨테이너 컴포넌트
const ResponsiveContainer = ({ 
  children, 
  maxWidth = 'desktop',
  padding = 'default',
  className = '',
  ...props 
}) => {
  const StyledContainer = styled(Container)`
    ${maxWidth === 'mobile' && `max-width: ${breakpoints.mobileLarge};`}
    ${maxWidth === 'tablet' && `max-width: ${breakpoints.tablet};`}
    ${maxWidth === 'laptop' && `max-width: ${breakpoints.laptop};`}
    ${maxWidth === 'desktop' && `max-width: ${breakpoints.desktop};`}
    
    ${padding === 'none' && 'padding: 0;'}
    ${padding === 'small' && 'padding: 0 12px;'}
    ${padding === 'large' && 'padding: 0 40px;'}
  `;

  return (
    <StyledContainer className={className} {...props}>
      {children}
    </StyledContainer>
  );
};

// 시각적 인디케이터 (개발용)
const DeviceIndicator = styled.div`
  position: fixed;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  z-index: 9999;
  pointer-events: none;
  
  ${process.env.NODE_ENV === 'production' && 'display: none;'}
`;

export const ShowDeviceType = () => {
  const { deviceType, screenSize } = useDeviceType();
  
  return (
    <DeviceIndicator>
      {deviceType} ({screenSize.width}×{screenSize.height})
    </DeviceIndicator>
  );
};

// 내보내기
export {
  ResponsiveContainer as default,
  Container,
  Grid,
  Flex,
  ResponsiveText,
  Spacer,
  ResponsiveCard,
  ResponsiveButton,
  ResponsiveInput,
  ResponsiveNav,
  HamburgerButton,
  breakpoints,
};