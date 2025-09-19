import React from 'react';
import styled, { keyframes } from 'styled-components';

// StockPilot 로고 애니메이션
const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

const LogoContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  
  &:hover .logo-icon {
    animation: ${pulseAnimation} 0.6s ease-in-out;
  }
`;

const LogoIcon = styled.div`
  position: relative;
  width: ${props => props.size || '40px'};
  height: ${props => props.size || '40px'};
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  
  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 70%;
    height: 70%;
    background: white;
    border-radius: 6px;
    opacity: 0.95;
  }
  
  .chart-icon {
    position: relative;
    z-index: 1;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: flex-end;
    gap: 2px;
  }
  
  .bar {
    background: linear-gradient(to top, #667eea, #764ba2);
    border-radius: 1px;
    transition: all 0.3s ease;
  }
  
  .bar-1 { width: 3px; height: 8px; }
  .bar-2 { width: 3px; height: 12px; }
  .bar-3 { width: 3px; height: 6px; }
  .bar-4 { width: 3px; height: 14px; }
  .bar-5 { width: 3px; height: 10px; }
`;

const LogoText = styled.div`
  display: flex;
  flex-direction: column;
  
  .main-text {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    font-size: ${props => props.textSize || '24px'};
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 2px;
  }
  
  .sub-text {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    font-size: ${props => Math.round((parseFloat(props.textSize) || 24) * 0.4)}px;
    font-weight: 500;
    color: #6B7280;
    line-height: 1;
    letter-spacing: 0.5px;
  }
`;

const SVGLogo = styled.svg`
  width: ${props => props.size || '40px'};
  height: ${props => props.size || '40px'};
  
  .logo-bg {
    fill: url(#logoGradient);
    filter: drop-shadow(0 4px 15px rgba(102, 126, 234, 0.3));
  }
  
  .chart-bar {
    fill: url(#chartGradient);
    transition: transform 0.3s ease;
  }
  
  &:hover .chart-bar {
    &:nth-child(1) { transform: scaleY(1.2); }
    &:nth-child(2) { transform: scaleY(1.1); }
    &:nth-child(3) { transform: scaleY(1.3); }
    &:nth-child(4) { transform: scaleY(1.15); }
    &:nth-child(5) { transform: scaleY(1.25); }
  }
`;

const Logo = ({ 
  size = '40px', 
  textSize = '24px', 
  showText = true, 
  variant = 'default',
  className = '',
  onClick,
  style = 'svg' // 'svg' or 'styled'
}) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      // 기본 홈페이지로 이동
      window.location.href = '/';
    }
  };

  if (style === 'svg') {
    return (
      <LogoContainer className={`logo-container ${className}`} onClick={handleClick}>
        <SVGLogo size={size} className="logo-icon">
          <defs>
            <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#764ba2" />
            </linearGradient>
            <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#667eea" />
              <stop offset="100%" stopColor="#764ba2" />
            </linearGradient>
            <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#f8fafc" stopOpacity="0.95" />
            </linearGradient>
          </defs>
          
          {/* 로고 배경 */}
          <rect 
            className="logo-bg"
            width="100%" 
            height="100%" 
            rx="12" 
            ry="12" 
          />
          
          {/* 내부 배경 */}
          <rect 
            x="15%" 
            y="15%" 
            width="70%" 
            height="70%" 
            rx="6" 
            ry="6" 
            fill="url(#bgGradient)" 
          />
          
          {/* 차트 바들 */}
          <g transform="translate(30%, 35%)">
            <rect className="chart-bar" x="0" y="40%" width="6%" height="60%" rx="1" />
            <rect className="chart-bar" x="12%" y="20%" width="6%" height="80%" rx="1" />
            <rect className="chart-bar" x="24%" y="50%" width="6%" height="50%" rx="1" />
            <rect className="chart-bar" x="36%" y="10%" width="6%" height="90%" rx="1" />
            <rect className="chart-bar" x="48%" y="30%" width="6%" height="70%" rx="1" />
          </g>
        </SVGLogo>
        
        {showText && (
          <LogoText textSize={textSize}>
            <div className="main-text">
              {variant === 'en' ? 'StockPilot' : '스톡파일럿'}
            </div>
            <div className="sub-text">
              {variant === 'en' ? 'AI Investment Copilot' : 'AI 투자 코파일럿'}
            </div>
          </LogoText>
        )}
      </LogoContainer>
    );
  }

  // Styled Components 버전
  return (
    <LogoContainer className={`logo-container ${className}`} onClick={handleClick}>
      <LogoIcon size={size} className="logo-icon">
        <div className="chart-icon">
          <div className="bar bar-1"></div>
          <div className="bar bar-2"></div>
          <div className="bar bar-3"></div>
          <div className="bar bar-4"></div>
          <div className="bar bar-5"></div>
        </div>
      </LogoIcon>
      
      {showText && (
        <LogoText textSize={textSize}>
          <div className="main-text">
            {variant === 'en' ? 'StockPilot' : '스톡파일럿'}
          </div>
          <div className="sub-text">
            {variant === 'en' ? 'AI Investment Copilot' : 'AI 투자 코파일럿'}
          </div>
        </LogoText>
      )}
    </LogoContainer>
  );
};

// 파비콘용 미니 로고
export const FaviconLogo = ({ size = '32px' }) => (
  <SVGLogo size={size}>
    <defs>
      <linearGradient id="faviconGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" />
        <stop offset="100%" stopColor="#764ba2" />
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" rx="8" ry="8" fill="url(#faviconGradient)" />
    <rect x="20%" y="20%" width="60%" height="60%" rx="4" ry="4" fill="white" opacity="0.95" />
    <g transform="translate(35%, 40%)">
      <rect x="0" y="40%" width="8%" height="60%" rx="1" fill="url(#faviconGradient)" />
      <rect x="15%" y="20%" width="8%" height="80%" rx="1" fill="url(#faviconGradient)" />
      <rect x="30%" y="50%" width="8%" height="50%" rx="1" fill="url(#faviconGradient)" />
      <rect x="45%" y="10%" width="8%" height="90%" rx="1" fill="url(#faviconGradient)" />
    </g>
  </SVGLogo>
);

// 로딩 애니메이션용 로고
export const LoadingLogo = ({ size = '60px' }) => {
  const loadingAnimation = keyframes`
    0% { opacity: 0.3; transform: scaleY(0.5); }
    50% { opacity: 1; transform: scaleY(1); }
    100% { opacity: 0.3; transform: scaleY(0.5); }
  `;

  const AnimatedSVG = styled(SVGLogo)`
    .chart-bar {
      animation: ${loadingAnimation} 1.5s ease-in-out infinite;
      transform-origin: bottom;
      
      &:nth-child(1) { animation-delay: 0s; }
      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
      &:nth-child(4) { animation-delay: 0.6s; }
      &:nth-child(5) { animation-delay: 0.8s; }
    }
  `;

  return (
    <AnimatedSVG size={size}>
      <defs>
        <linearGradient id="loadingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#667eea" />
          <stop offset="100%" stopColor="#764ba2" />
        </linearGradient>
      </defs>
      <rect className="logo-bg" width="100%" height="100%" rx="12" ry="12" />
      <rect x="15%" y="15%" width="70%" height="70%" rx="6" ry="6" fill="white" opacity="0.95" />
      <g transform="translate(30%, 35%)">
        <rect className="chart-bar" x="0" y="40%" width="6%" height="60%" rx="1" />
        <rect className="chart-bar" x="12%" y="20%" width="6%" height="80%" rx="1" />
        <rect className="chart-bar" x="24%" y="50%" width="6%" height="50%" rx="1" />
        <rect className="chart-bar" x="36%" y="10%" width="6%" height="90%" rx="1" />
        <rect className="chart-bar" x="48%" y="30%" width="6%" height="70%" rx="1" />
      </g>
    </AnimatedSVG>
  );
};

export default Logo;