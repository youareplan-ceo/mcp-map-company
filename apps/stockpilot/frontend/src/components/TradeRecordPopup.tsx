/**
 * 거래 기록 입력 팝업 - 토스 스타일
 * 매수/매도 기록을 간단하게 입력할 수 있는 팝업
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Stack,
  IconButton,
  Divider
} from '@mui/material';
import {
  Close as CloseIcon,
  TrendingUp as BuyIcon,
  TrendingDown as SellIcon
} from '@mui/icons-material';

// 토스 스타일 색상
const tossColors = {
  primary: '#3182F6',
  profit: '#00C73C',
  loss: '#FF5A5F',
  neutral: '#8B95A1',
  background: '#F2F4F6',
  cardBg: '#FFFFFF',
  textPrimary: '#191F28',
  textSecondary: '#6B7684',
  border: '#E5E8EB'
};

interface TradeRecordPopupProps {
  open: boolean;
  onClose: () => void;
  stockName?: string;
  stockSymbol?: string;
}

interface TradeRecord {
  type: 'buy' | 'sell';
  quantity: string;
  price: string;
}

export const TradeRecordPopup: React.FC<TradeRecordPopupProps> = ({
  open,
  onClose,
  stockName = '',
  stockSymbol = ''
}) => {
  const [tradeRecord, setTradeRecord] = useState<TradeRecord>({
    type: 'buy',
    quantity: '',
    price: ''
  });

  // 입력값 검증
  const isValid = tradeRecord.quantity && tradeRecord.price && 
                  !isNaN(Number(tradeRecord.quantity)) && 
                  !isNaN(Number(tradeRecord.price)) &&
                  Number(tradeRecord.quantity) > 0 &&
                  Number(tradeRecord.price) > 0;

  const handleSave = () => {
    if (!isValid) return;

    // 거래 기록 저장 로직
    console.log('거래 기록 저장:', {
      stockName,
      stockSymbol,
      type: tradeRecord.type,
      quantity: Number(tradeRecord.quantity),
      price: Number(tradeRecord.price),
      total: Number(tradeRecord.quantity) * Number(tradeRecord.price),
      date: new Date().toISOString()
    });

    // 팝업 닫기
    handleClose();
  };

  const handleClose = () => {
    setTradeRecord({
      type: 'buy',
      quantity: '',
      price: ''
    });
    onClose();
  };

  const totalAmount = tradeRecord.quantity && tradeRecord.price 
    ? (Number(tradeRecord.quantity) * Number(tradeRecord.price)).toLocaleString()
    : '0';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      sx={{
        '& .MuiDialog-paper': {
          borderRadius: 3,
          m: 2
        }
      }}
    >
      <DialogTitle sx={{ p: 3, pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: tossColors.textPrimary }}>
              거래 기록 입력
            </Typography>
            {stockName && (
              <Typography variant="body2" sx={{ color: tossColors.textSecondary, mt: 0.5 }}>
                {stockName} ({stockSymbol})
              </Typography>
            )}
          </Box>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Stack spacing={3}>
          {/* 매수/매도 선택 */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: tossColors.textPrimary }}>
              거래 유형
            </Typography>
            <ToggleButtonGroup
              value={tradeRecord.type}
              exclusive
              onChange={(_, newType) => newType && setTradeRecord(prev => ({ ...prev, type: newType }))}
              fullWidth
              sx={{
                '& .MuiToggleButton-root': {
                  py: 2,
                  border: `1px solid ${tossColors.border}`,
                  '&.Mui-selected': {
                    bgcolor: tradeRecord.type === 'buy' ? tossColors.profit : tossColors.loss,
                    color: 'white',
                    '&:hover': {
                      bgcolor: tradeRecord.type === 'buy' ? tossColors.profit : tossColors.loss,
                    }
                  }
                }
              }}
            >
              <ToggleButton value="buy" sx={{ borderRadius: '8px 0 0 8px' }}>
                <BuyIcon sx={{ mr: 1 }} />
                매수
              </ToggleButton>
              <ToggleButton value="sell" sx={{ borderRadius: '0 8px 8px 0' }}>
                <SellIcon sx={{ mr: 1 }} />
                매도
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {/* 수량 입력 */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: tossColors.textPrimary }}>
              수량
            </Typography>
            <TextField
              fullWidth
              placeholder="수량을 입력하세요"
              value={tradeRecord.quantity}
              onChange={(e) => setTradeRecord(prev => ({ ...prev, quantity: e.target.value }))}
              type="number"
              inputProps={{ min: 0, step: 1 }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  '& fieldset': {
                    borderColor: tossColors.border,
                  }
                }
              }}
            />
          </Box>

          {/* 가격 입력 */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600, color: tossColors.textPrimary }}>
              가격 (원)
            </Typography>
            <TextField
              fullWidth
              placeholder="가격을 입력하세요"
              value={tradeRecord.price}
              onChange={(e) => setTradeRecord(prev => ({ ...prev, price: e.target.value }))}
              type="number"
              inputProps={{ min: 0, step: 0.01 }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  '& fieldset': {
                    borderColor: tossColors.border,
                  }
                }
              }}
            />
          </Box>

          {/* 총 금액 표시 */}
          <Box sx={{ bgcolor: tossColors.background, p: 2, borderRadius: 2 }}>
            <Typography variant="body2" sx={{ color: tossColors.textSecondary, mb: 1 }}>
              총 {tradeRecord.type === 'buy' ? '매수' : '매도'} 금액
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: tossColors.textPrimary }}>
              {totalAmount}원
            </Typography>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button
          onClick={handleClose}
          variant="outlined"
          sx={{
            borderColor: tossColors.border,
            color: tossColors.textSecondary,
            '&:hover': {
              borderColor: tossColors.neutral,
              bgcolor: 'transparent'
            }
          }}
        >
          취소
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!isValid}
          sx={{
            bgcolor: tossColors.primary,
            '&:hover': {
              bgcolor: '#2564C7'
            },
            '&:disabled': {
              bgcolor: tossColors.neutral,
              color: 'white'
            }
          }}
        >
          저장
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TradeRecordPopup;