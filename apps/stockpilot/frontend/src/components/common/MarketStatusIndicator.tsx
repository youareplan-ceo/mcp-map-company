/**
 * 시장 상태 표시 컴포넌트
 * 미국 시장 상태를 우선으로 표시하고 한국 시장도 지원
 */

import React from 'react';
import { Box, Chip, Typography, Tooltip } from '@mui/material';
import {
  Circle as CircleIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import { 
  getMarketStatus, 
  getMarketByCode, 
  US_MARKET, 
  KR_MARKET, 
  MarketStatus as MarketStatusType 
} from '../../config/marketConfig';

interface Props {
  marketCode?: string;
  showTime?: boolean;
  size?: 'small' | 'medium';
}

export const MarketStatusIndicator: React.FC<Props> = ({
  marketCode = 'US',
  showTime = true,
  size = 'medium'
}) => {
  const marketConfig = getMarketByCode(marketCode);
  const status = getMarketStatus(marketConfig);
  
  const getStatusColor = (status: MarketStatusType) => {
    switch (status) {
      case 'OPEN':
        return 'success';
      case 'PRE_MARKET':
      case 'AFTER_HOURS':
        return 'warning';
      case 'CLOSED':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: MarketStatusType) => {
    switch (status) {
      case 'OPEN':
        return '장중';
      case 'PRE_MARKET':
        return '장전';
      case 'AFTER_HOURS':
        return '장후';
      case 'CLOSED':
        return '휴장';
      default:
        return '알 수 없음';
    }
  };

  const getStatusIcon = (status: MarketStatusType) => {
    const iconProps = { fontSize: size === 'small' ? 'small' : 'medium' } as const;
    
    switch (status) {
      case 'OPEN':
        return <CircleIcon color="success" {...iconProps} />;
      case 'PRE_MARKET':
      case 'AFTER_HOURS':
        return <CircleIcon color="warning" {...iconProps} />;
      case 'CLOSED':
        return <CircleIcon color="error" {...iconProps} />;
      default:
        return <CircleIcon color="disabled" {...iconProps} />;
    }
  };

  const getCurrentTime = () => {
    return new Intl.DateTimeFormat(marketConfig.locale, {
      timeZone: marketConfig.timezone,
      hour12: marketConfig.code === 'US',
      hour: '2-digit',
      minute: '2-digit',
      second: showTime ? '2-digit' : undefined,
    }).format(new Date());
  };

  const getMarketHours = () => {
    return `${marketConfig.openTime} - ${marketConfig.closeTime}`;
  };

  return (
    <Tooltip
      title={
        <Box>
          <Typography variant="body2" fontWeight={600}>
            {marketConfig.name}
          </Typography>
          <Typography variant="caption">
            거래 시간: {getMarketHours()} ({marketConfig.timezone})
          </Typography>
          <Typography variant="caption" display="block">
            현재 시간: {getCurrentTime()}
          </Typography>
        </Box>
      }
    >
      <Box display="flex" alignItems="center" gap={1}>
        <Chip
          icon={getStatusIcon(status)}
          label={
            <Box display="flex" alignItems="center" gap={0.5}>
              <Typography
                variant={size === 'small' ? 'caption' : 'body2'}
                fontWeight={600}
              >
                {marketConfig.code} {getStatusText(status)}
              </Typography>
            </Box>
          }
          color={getStatusColor(status) as any}
          size={size}
          variant="outlined"
        />
        
        {showTime && (
          <Box display="flex" alignItems="center" gap={0.5}>
            <TimeIcon fontSize="small" color="action" />
            <Typography
              variant={size === 'small' ? 'caption' : 'body2'}
              color="text.secondary"
            >
              {getCurrentTime()}
            </Typography>
          </Box>
        )}
      </Box>
    </Tooltip>
  );
};