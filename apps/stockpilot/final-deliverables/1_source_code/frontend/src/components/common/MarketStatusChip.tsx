/**
 * 시장 상태 표시 칩 컴포넌트
 * 한국 주식시장의 현재 상태를 실시간으로 표시
 */

import React, { useState, useEffect } from 'react';
import {
  Chip,
  Typography,
  Box,
  Tooltip
} from '@mui/material';
import {
  Schedule as ScheduleIcon,
  TrendingUp as OpenIcon,
  TrendingFlat as ClosedIcon
} from '@mui/icons-material';
import { DateUtils } from '../../utils';
import { useQuery } from '@tanstack/react-query';
import { MarketService } from '../../services/api';

const MarketStatusChip: React.FC = () => {
  const [currentTime, setCurrentTime] = useState(new Date());

  // 현재 시간 업데이트
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 시장 상태 조회
  const { data: marketStatus } = useQuery({
    queryKey: ['marketStatus'],
    queryFn: () => MarketService.getMarketStatus(),
    refetchInterval: 60000, // 1분마다 갱신
    staleTime: 30000 // 30초간 캐시 유지
  });

  const isMarketOpen = marketStatus?.isOpen ?? DateUtils.isMarketHours();
  const minutesToClose = DateUtils.minutesToMarketClose();

  const getStatusColor = () => {
    if (!DateUtils.isTradingDay()) return 'default';
    return isMarketOpen ? 'success' : 'warning';
  };

  const getStatusLabel = () => {
    if (!DateUtils.isTradingDay()) {
      return '휴장';
    }
    return isMarketOpen ? '장중' : '장마감';
  };

  const getStatusIcon = () => {
    if (!DateUtils.isTradingDay()) {
      return <ScheduleIcon fontSize="small" />;
    }
    return isMarketOpen ? <OpenIcon fontSize="small" /> : <ClosedIcon fontSize="small" />;
  };

  const getTooltipContent = () => {
    if (!DateUtils.isTradingDay()) {
      return (
        <Box>
          <Typography variant="body2">주말 및 공휴일은 휴장입니다</Typography>
          <Typography variant="caption" color="text.secondary">
            다음 거래일: {marketStatus?.nextTradingDay || '월요일'}
          </Typography>
        </Box>
      );
    }

    if (isMarketOpen) {
      const remainingTime = Math.max(minutesToClose, 0);
      const hours = Math.floor(remainingTime / 60);
      const minutes = remainingTime % 60;
      
      return (
        <Box>
          <Typography variant="body2">한국 주식시장 개장 중</Typography>
          <Typography variant="caption" color="text.secondary">
            거래시간: 09:00 - 15:30
          </Typography>
          {remainingTime > 0 && (
            <Typography variant="caption" display="block">
              마감까지: {hours > 0 ? `${hours}시간 ` : ''}{minutes}분
            </Typography>
          )}
        </Box>
      );
    }

    return (
      <Box>
        <Typography variant="body2">한국 주식시장 마감</Typography>
        <Typography variant="caption" color="text.secondary">
          거래시간: 09:00 - 15:30
        </Typography>
        <Typography variant="caption" display="block">
          다음 개장: 익일 09:00
        </Typography>
      </Box>
    );
  };

  return (
    <Box>
      <Tooltip title={getTooltipContent()} arrow>
        <Chip
          icon={getStatusIcon()}
          label={getStatusLabel()}
          color={getStatusColor()}
          size="small"
          variant="outlined"
          sx={{
            width: '100%',
            justifyContent: 'flex-start',
            '& .MuiChip-icon': {
              marginLeft: '8px'
            }
          }}
        />
      </Tooltip>
      
      {/* 현재 시간 표시 */}
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{
          display: 'block',
          textAlign: 'center',
          mt: 0.5,
          fontSize: '0.75rem'
        }}
      >
        {DateUtils.formatMarketTime(currentTime)}
      </Typography>
    </Box>
  );
};

export default MarketStatusChip;