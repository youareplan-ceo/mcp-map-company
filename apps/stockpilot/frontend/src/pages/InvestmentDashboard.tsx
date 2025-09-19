/**
 * 자산 증식 코치 - 홈 화면
 * 평소엔 조용, 중요할 때만 알림
 * 최상단: 내 총자산 (크게)
 * 중앙: 상태 표시 (평소엔 안정, 액션시에만 알림)
 * 하단: 비움 (깨끗하게)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon
} from '@mui/icons-material';

// 자산 증식 코치 색상
const coachColors = {
  background: '#F7F8FA',  // 토스 그레이
  cardBg: '#FFFFFF',      // 흰색 카드
  profit: '#00C853',      // 수익 녹색
  loss: '#FF5252',        // 손실 빨강
  primary: '#4B8BF5',     // 토스 블루
  text: '#1A1A1A',        // 검정 텍스트
  textSecondary: '#666666', // 회색 텍스트
  stable: '#00C853',      // 안정 상태
  action: '#FF5252'       // 액션 필요
};

// 자산 현황 타입
interface AssetStatus {
  totalValue: number;     // 총 자산
  totalProfit: number;    // 총 수익금액
  profitRate: number;     // 수익률
}

// 상태 알림 타입
interface StatusAlert {
  id: string;
  type: 'stable' | 'action';
  message: string;
  details?: string;
}

export const InvestmentDashboard: React.FC = () => {
  const navigate = useNavigate();
  
  // 자산 증식 코치 상태 관리
  const [assetStatus, setAssetStatus] = useState<AssetStatus | null>(null);
  const [statusAlert, setStatusAlert] = useState<StatusAlert | null>(null);
  const [loading, setLoading] = useState(false);

  // 데이터 로드
  useEffect(() => {
    loadAssetData();
  }, []);

  // 자산 데이터 로드
  const loadAssetData = async () => {
    setLoading(true);
    try {
      // 자산 현황 데이터
      setAssetStatus({
        totalValue: 2450000,
        totalProfit: 320000,
        profitRate: 15.2
      });

      // 상태 알림 (평소엔 안정, 중요시에만 액션)
      // 예시: 평소엔 안정 상태
      setStatusAlert({
        id: 'status-1',
        type: 'stable',
        message: '포트폴리오 안정 ✅'
      });
      
      // 액션 필요시 예시:
      // setStatusAlert({
      //   id: 'action-1',
      //   type: 'action',
      //   message: '🔴 AAPL 240불 매도',
      //   details: '목표 수익률 달성'
      // });

    } catch (error) {
      console.error('자산 데이터 로드 실패:', error);
    }
    setLoading(false);
  };

  // 수익률 색상 결정
  const getProfitColor = (value: number) => {
    return value > 0 ? coachColors.profit : coachColors.loss;
  };

  // 상태 아이콘 결정
  const getStatusIcon = (type: StatusAlert['type']) => {
    return type === 'stable' ? 
      <CheckIcon sx={{ fontSize: 24, color: coachColors.stable }} /> :
      <WarningIcon sx={{ fontSize: 24, color: coachColors.action }} />;
  };

  // 상태 색상 결정
  const getStatusColor = (type: StatusAlert['type']) => {
    return type === 'stable' ? coachColors.stable : coachColors.action;
  };

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: coachColors.background,
      pb: { xs: 9, sm: 4 },
      p: 3
    }}>
      {/* 최상단: 내 총자산 (크게) */}
      <Card 
        sx={{
          bgcolor: coachColors.cardBg,
          borderRadius: '12px',
          mb: 3,
          p: 3,
          textAlign: 'center',
          boxShadow: 'none'
        }}
      >
        <Typography 
          variant="body2" 
          sx={{ 
            color: coachColors.textSecondary,
            mb: 2,
            fontSize: '16px'
          }}
        >
          내 총자산
        </Typography>
        
        {assetStatus && (
          <>
            <Typography 
              sx={{ 
                fontSize: '32px',
                fontWeight: 700,
                color: coachColors.text,
                mb: 3
              }}
            >
              {assetStatus.totalValue.toLocaleString()}원
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 4 }}>
              <Box>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: getProfitColor(assetStatus.totalProfit)
                  }}
                >
                  {assetStatus.totalProfit > 0 ? '+' : ''}{assetStatus.totalProfit.toLocaleString()}원
                </Typography>
              </Box>
              <Box>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: getProfitColor(assetStatus.profitRate)
                  }}
                >
                  {assetStatus.profitRate > 0 ? '+' : ''}{assetStatus.profitRate.toFixed(1)}%
                </Typography>
              </Box>
            </Box>
          </>
        )}
      </Card>

      {/* 중앙: 상태 표시 (평소엔 안정, 액션시에만 알림) */}
      {statusAlert && (
        <Card 
          sx={{
            bgcolor: coachColors.cardBg,
            borderRadius: '12px',
            mb: 3,
            p: 3,
            textAlign: 'center',
            boxShadow: 'none',
            border: `2px solid ${getStatusColor(statusAlert.type)}`
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
            {getStatusIcon(statusAlert.type)}
            <Typography 
              sx={{ 
                fontSize: '16px',
                fontWeight: 600,
                color: getStatusColor(statusAlert.type)
              }}
            >
              {statusAlert.message}
            </Typography>
          </Box>
          
          {statusAlert.details && (
            <Typography 
              sx={{ 
                fontSize: '14px',
                color: coachColors.textSecondary
              }}
            >
              {statusAlert.details}
            </Typography>
          )}
        </Card>
      )}

      {/* 하단: 비움 (깨끗하게) */}
      <Box sx={{ height: '40vh' }} />
    </Box>
  );
};

export default InvestmentDashboard;