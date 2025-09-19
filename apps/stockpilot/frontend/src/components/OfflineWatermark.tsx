/**
 * 오프라인 프리뷰 모드 워터마크 컴포넌트
 */

import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { CloudOff as OfflineIcon } from '@mui/icons-material';

interface OfflineWatermarkProps {
  visible?: boolean;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

export const OfflineWatermark: React.FC<OfflineWatermarkProps> = ({
  visible = true,
  position = 'top-right'
}) => {
  if (!visible) return null;

  const positionStyles = {
    'top-left': { top: 16, left: 16 },
    'top-right': { top: 16, right: 16 },
    'bottom-left': { bottom: 16, left: 16 },
    'bottom-right': { bottom: 16, right: 16 }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        ...positionStyles[position],
        zIndex: 9999,
        backgroundColor: 'rgba(255, 193, 7, 0.9)',
        backdropFilter: 'blur(4px)',
        borderRadius: 2,
        px: 2,
        py: 1,
        border: '2px solid #ff9800',
        boxShadow: '0 4px 12px rgba(255, 152, 0, 0.3)',
        animation: 'pulse 2s infinite'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <OfflineIcon sx={{ color: '#e65100', fontSize: 20 }} />
        <Typography
          variant="body2"
          sx={{
            color: '#e65100',
            fontWeight: 'bold',
            fontSize: '0.85rem',
            textShadow: '1px 1px 2px rgba(255, 255, 255, 0.8)'
          }}
        >
          OFFLINE PREVIEW
        </Typography>
      </Box>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </Box>
  );
};

export default OfflineWatermark;