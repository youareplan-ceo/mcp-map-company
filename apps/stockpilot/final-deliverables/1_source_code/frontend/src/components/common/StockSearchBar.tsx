/**
 * 종목 검색 바 컴포넌트
 * 한국 주식 종목명과 코드 검색 지원
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Autocomplete,
  TextField,
  Paper,
  Box,
  Typography,
  Chip,
  CircularProgress,
  InputAdornment
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { StockService } from '../../services/api';
import { StockSearchResult } from '../../types';
import { MarketUtils, NumberUtils } from '../../utils';
import { useNavigate } from 'react-router-dom';
import { debounce } from 'lodash';

interface StockSearchBarProps {
  placeholder?: string;
  onSelect?: (stock: StockSearchResult) => void;
  autoNavigate?: boolean;
  fullWidth?: boolean;
  size?: 'small' | 'medium';
}

const StockSearchBar: React.FC<StockSearchBarProps> = ({
  placeholder = '종목명 또는 코드를 검색하세요',
  onSelect,
  autoNavigate = true,
  fullWidth = true,
  size = 'medium'
}) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(false);
  const debounceRef = useRef<any>();

  // 검색 디바운싱
  const debouncedSearch = debounce((query: string) => {
    setSearchQuery(query);
  }, 300);

  // 검색 결과 조회
  const { data: searchResults = [], isLoading } = useQuery({
    queryKey: ['stockSearch', searchQuery],
    queryFn: () => StockService.searchStocks(searchQuery, 10),
    enabled: searchQuery.length >= 1,
    staleTime: 30000, // 30초간 캐시 유지
  });

  // 검색어 변경 처리
  const handleInputChange = (event: React.SyntheticEvent, value: string) => {
    debouncedSearch(value);
  };

  // 종목 선택 처리
  const handleStockSelect = (event: React.SyntheticEvent, value: StockSearchResult | null) => {
    if (!value) return;

    // 콜백 함수 호출
    if (onSelect) {
      onSelect(value);
    }

    // 자동 네비게이션
    if (autoNavigate) {
      navigate(`/analysis/${value.symbol}`);
    }
  };

  // 옵션 렌더링
  const renderOption = (props: any, option: StockSearchResult) => (
    <Box
      component="li"
      {...props}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        p: 1.5,
        '&:hover': {
          backgroundColor: 'action.hover'
        }
      }}
    >
      {/* 종목 기본 정보 */}
      <Box sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            {option.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            ({option.symbol})
          </Typography>
          <Chip
            label={MarketUtils.getMarketLabel(option.market)}
            size="small"
            variant="outlined"
            sx={{
              height: 20,
              fontSize: '0.7rem',
              color: MarketUtils.getMarketColor(option.market),
              borderColor: MarketUtils.getMarketColor(option.market)
            }}
          />
        </Box>
        <Typography variant="caption" color="text.secondary">
          {option.sector}
        </Typography>
      </Box>

      {/* 주가 정보 (있는 경우) */}
      {option.currentPrice && (
        <Box sx={{ textAlign: 'right', minWidth: 80 }}>
          <Typography variant="body2" fontWeight={600}>
            {NumberUtils.formatPrice(option.currentPrice)}원
          </Typography>
          {option.changeRate !== undefined && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {option.changeRate > 0 ? (
                <TrendingUpIcon sx={{ fontSize: 16, color: 'error.main' }} />
              ) : option.changeRate < 0 ? (
                <TrendingDownIcon sx={{ fontSize: 16, color: 'primary.main' }} />
              ) : null}
              <Typography
                variant="caption"
                sx={{
                  color: MarketUtils.getPriceChangeColor(option.changeRate),
                  fontWeight: 500
                }}
              >
                {MarketUtils.formatChangeRate(option.changeRate)}
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );

  // 입력 필드 렌더링
  const renderInput = (params: any) => (
    <TextField
      {...params}
      placeholder={placeholder}
      variant="outlined"
      size={size}
      fullWidth={fullWidth}
      onFocus={() => setIsInputFocused(true)}
      onBlur={() => setIsInputFocused(false)}
      InputProps={{
        ...params.InputProps,
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon color="action" />
          </InputAdornment>
        ),
        endAdornment: (
          <>
            {isLoading && (
              <InputAdornment position="end">
                <CircularProgress size={20} />
              </InputAdornment>
            )}
            {params.InputProps.endAdornment}
          </>
        )
      }}
      sx={{
        '& .MuiOutlinedInput-root': {
          borderRadius: 2,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: 'primary.main'
            }
          },
          '&.Mui-focused': {
            '& .MuiOutlinedInput-notchedOutline': {
              borderWidth: 2
            }
          }
        }
      }}
    />
  );

  // 검색 결과가 없을 때 렌더링
  const renderNoOptionsText = () => {
    if (isLoading) return '검색 중...';
    if (searchQuery.length === 0) return '종목명 또는 코드를 입력하세요';
    return '검색 결과가 없습니다';
  };

  // cleanup
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        debounceRef.current.cancel();
      }
    };
  }, []);

  return (
    <Autocomplete
      options={searchResults}
      getOptionLabel={(option) => `${option.name} (${option.symbol})`}
      renderOption={renderOption}
      renderInput={renderInput}
      noOptionsText={renderNoOptionsText()}
      onChange={handleStockSelect}
      onInputChange={handleInputChange}
      loading={isLoading}
      clearOnBlur={false}
      selectOnFocus
      handleHomeEndKeys
      PaperComponent={({ children, ...other }) => (
        <Paper
          {...other}
          elevation={8}
          sx={{
            mt: 1,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            '& .MuiAutocomplete-listbox': {
              padding: 0,
              maxHeight: 400
            },
            '& .MuiAutocomplete-option': {
              padding: 0
            }
          }}
        >
          {children}
        </Paper>
      )}
      sx={{
        '& .MuiAutocomplete-inputRoot': {
          paddingRight: '9px !important'
        }
      }}
    />
  );
};

export default StockSearchBar;