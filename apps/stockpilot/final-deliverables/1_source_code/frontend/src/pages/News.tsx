/**
 * 뉴스 분석 페이지
 * 한국 주식시장 관련 뉴스와 AI 감정 분석 결과 제공
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Button,
  ButtonGroup,
  TextField,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Divider,
  Tab,
  Tabs,
  Alert,
  LinearProgress,
  IconButton,
  Link
} from '@mui/material';
import {
  TrendingUp as PositiveIcon,
  TrendingDown as NegativeIcon,
  TrendingFlat as NeutralIcon,
  OpenInNew as OpenIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { NewsService } from '../services/api';
import { NewsItem, NewsSentiment, NewsCategory, NewsFilters, NewsSummary, TrendingKeyword, NEWS_SENTIMENT } from '../types/news';
import { DateUtils, NumberUtils } from '../utils';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ paddingTop: 16 }}>
    {value === index && children}
  </div>
);


const News: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [filters, setFilters] = useState<NewsFilters>({ period: '1d' });
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());

  // 뉴스 목록 조회
  const { data: newsData, isLoading, refetch } = useQuery({
    queryKey: ['news', filters],
    queryFn: () => NewsService.getNews(filters),
    refetchInterval: 300000 // 5분마다 갱신
  });

  // 뉴스 요약 통계
  const { data: newsSummary } = useQuery({
    queryKey: ['newsSummary', filters],
    queryFn: () => NewsService.getNewsSummary(filters),
    refetchInterval: 300000
  });

  // 트렌딩 키워드
  const { data: trendingKeywords = [] } = useQuery({
    queryKey: ['trendingKeywords', filters],
    queryFn: () => NewsService.getTrendingKeywords(filters),
    refetchInterval: 600000 // 10분마다 갱신
  });

  // 시장 영향도 높은 뉴스
  const { data: impactfulNews = [] } = useQuery({
    queryKey: ['impactfulNews', filters],
    queryFn: () => NewsService.getImpactfulNews(filters),
    refetchInterval: 300000
  });

  const getSentimentIcon = (sentiment: NewsSentiment) => {
    switch (sentiment) {
      case NEWS_SENTIMENT.POSITIVE:
        return <PositiveIcon sx={{ color: 'success.main' }} />;
      case NEWS_SENTIMENT.NEGATIVE:
        return <NegativeIcon sx={{ color: 'error.main' }} />;
      default:
        return <NeutralIcon sx={{ color: 'grey.500' }} />;
    }
  };

  const getSentimentColor = (sentiment: NewsSentiment) => {
    switch (sentiment) {
      case NEWS_SENTIMENT.POSITIVE:
        return 'success';
      case NEWS_SENTIMENT.NEGATIVE:
        return 'error';
      default:
        return 'default';
    }
  };

  const getSentimentLabel = (sentiment: NewsSentiment) => {
    switch (sentiment) {
      case NEWS_SENTIMENT.POSITIVE:
        return '긍정적';
      case NEWS_SENTIMENT.NEGATIVE:
        return '부정적';
      default:
        return '중립적';
    }
  };

  const handleFilterChange = (key: keyof NewsFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const toggleBookmark = (articleId: string) => {
    const newBookmarks = new Set(bookmarks);
    if (newBookmarks.has(articleId)) {
      newBookmarks.delete(articleId);
    } else {
      newBookmarks.add(articleId);
    }
    setBookmarks(newBookmarks);
  };

  // 요약 통계 카드
  const summaryCards = [
    {
      title: '총 뉴스',
      value: newsSummary?.totalNews || 0,
      icon: <FilterIcon />
    },
    {
      title: '긍정적 뉴스',
      value: newsSummary?.positiveNews || 0,
      icon: <PositiveIcon />,
      color: 'success.main'
    },
    {
      title: '부정적 뉴스',
      value: newsSummary?.negativeNews || 0,
      icon: <NegativeIcon />,
      color: 'error.main'
    },
    {
      title: '평균 감정점수',
      value: newsSummary?.averageSentiment ? NumberUtils.formatNumber(newsSummary.averageSentiment, 2) : '-',
      icon: <NeutralIcon />
    }
  ];

  return (
    <Box>
      {/* 헤더 */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          뉴스 분석
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => refetch()}
        >
          새로고침
        </Button>
      </Box>

      {/* 요약 통계 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {summaryCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                      {card.title}
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {card.value}
                    </Typography>
                  </Box>
                  <Box sx={{ color: card.color || 'primary.main' }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 필터 및 탭 */}
      <Paper sx={{ mb: 3 }}>
        {/* 필터 바 */}
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item>
              <TextField
                select
                size="small"
                label="카테고리"
                value={filters.category || ''}
                onChange={(e) => handleFilterChange('category', e.target.value || undefined)}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="">전체</MenuItem>
                <MenuItem value="market">시장동향</MenuItem>
                <MenuItem value="economy">경제</MenuItem>
                <MenuItem value="corporate">기업</MenuItem>
                <MenuItem value="policy">정책</MenuItem>
                <MenuItem value="international">해외</MenuItem>
              </TextField>
            </Grid>
            <Grid item>
              <TextField
                select
                size="small"
                label="감정"
                value={filters.sentiment || ''}
                onChange={(e) => handleFilterChange('sentiment', e.target.value || undefined)}
                sx={{ minWidth: 100 }}
              >
                <MenuItem value="">전체</MenuItem>
                <MenuItem value={NEWS_SENTIMENT.POSITIVE}>긍정적</MenuItem>
                <MenuItem value={NEWS_SENTIMENT.NEUTRAL}>중립적</MenuItem>
                <MenuItem value={NEWS_SENTIMENT.NEGATIVE}>부정적</MenuItem>
              </TextField>
            </Grid>
            <Grid item>
              <ButtonGroup size="small">
                {(['1h', '6h', '1d', '3d', '1w'] as const).map((period) => (
                  <Button
                    key={period}
                    variant={filters.period === period ? 'contained' : 'outlined'}
                    onClick={() => handleFilterChange('period', period)}
                  >
                    {period === '1h' ? '1시간' : period === '6h' ? '6시간' : 
                     period === '1d' ? '1일' : period === '3d' ? '3일' : '1주일'}
                  </Button>
                ))}
              </ButtonGroup>
            </Grid>
          </Grid>
        </Box>

        {/* 탭 */}
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="전체 뉴스" />
          <Tab label="시장 영향 뉴스" />
          <Tab label="트렌딩 키워드" />
          <Tab label="북마크" />
        </Tabs>

        {/* 전체 뉴스 탭 */}
        <TabPanel value={tabValue} index={0}>
          {isLoading ? (
            <LinearProgress />
          ) : (
            <List sx={{ p: 0 }}>
              {newsData?.map((article, index) => (
                <React.Fragment key={article.id}>
                  <ListItem alignItems="flex-start" sx={{ py: 2 }}>
                    <ListItemAvatar>
                      <Avatar
                        variant="rounded"
                        src={article.imageUrl}
                        sx={{ width: 60, height: 60, mr: 2 }}
                      >
                        {article.source.charAt(0)}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <Link
                            href={article.url}
                            target="_blank"
                            rel="noopener"
                            sx={{
                              color: 'text.primary',
                              textDecoration: 'none',
                              fontWeight: 600,
                              fontSize: '1rem',
                              lineHeight: 1.4,
                              flexGrow: 1,
                              mr: 1,
                              '&:hover': {
                                textDecoration: 'underline'
                              }
                            }}
                          >
                            {article.title}
                          </Link>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <IconButton
                              size="small"
                              onClick={() => toggleBookmark(article.id)}
                              color={bookmarks.has(article.id) ? 'primary' : 'default'}
                            >
                              {bookmarks.has(article.id) ? <BookmarkIcon /> : <BookmarkBorderIcon />}
                            </IconButton>
                            <IconButton
                              size="small"
                              component="a"
                              href={article.url}
                              target="_blank"
                              rel="noopener"
                            >
                              <OpenIcon />
                            </IconButton>
                          </Box>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1, lineHeight: 1.5 }}>
                            {article.summary}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              icon={getSentimentIcon(article.sentiment)}
                              label={getSentimentLabel(article.sentiment)}
                              size="small"
                              color={getSentimentColor(article.sentiment)}
                              variant="outlined"
                            />
                            <Typography variant="caption" color="text.secondary">
                              {article.source}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              •
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {DateUtils.formatRelativeTime(new Date(article.publishedAt))}
                            </Typography>
                            {article.impactScore && (
                              <>
                                <Typography variant="caption" color="text.secondary">
                                  •
                                </Typography>
                                <Typography variant="caption" color="primary.main" fontWeight={500}>
                                  영향도: {NumberUtils.formatNumber(article.impactScore, 1)}
                                </Typography>
                              </>
                            )}
                          </Box>
                          {article.relatedStocks && article.relatedStocks.length > 0 && (
                            <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                              {article.relatedStocks.slice(0, 3).map((stock) => (
                                <Chip
                                  key={stock.symbol}
                                  label={`${stock.name} (${stock.symbol})`}
                                  size="small"
                                  variant="outlined"
                                  sx={{ fontSize: '0.7rem', height: 24 }}
                                />
                              ))}
                              {article.relatedStocks.length > 3 && (
                                <Typography variant="caption" color="text.secondary">
                                  외 {article.relatedStocks.length - 3}개
                                </Typography>
                              )}
                            </Box>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < (newsData?.length || 0) - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </TabPanel>

        {/* 시장 영향 뉴스 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              시장에 큰 영향을 줄 수 있는 뉴스
            </Typography>
            {impactfulNews.length > 0 ? (
              <Grid container spacing={2}>
                {impactfulNews.map((article) => (
                  <Grid item xs={12} md={6} key={article.id}>
                    <Card>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="h6" sx={{ flexGrow: 1, mr: 1 }}>
                            {article.title}
                          </Typography>
                          <Chip
                            label={`영향도 ${NumberUtils.formatNumber(article.impactScore || 0, 1)}`}
                            color="warning"
                            size="small"
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          {article.summary}
                        </Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getSentimentIcon(article.sentiment)}
                            <Typography variant="body2">
                              {getSentimentLabel(article.sentiment)}
                            </Typography>
                          </Box>
                          <Typography variant="caption" color="text.secondary">
                            {DateUtils.formatRelativeTime(new Date(article.publishedAt))}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info">
                현재 시장에 큰 영향을 줄 수 있는 뉴스가 없습니다.
              </Alert>
            )}
          </Box>
        </TabPanel>

        {/* 트렌딩 키워드 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              인기 검색 키워드
            </Typography>
            {trendingKeywords.length > 0 ? (
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {trendingKeywords.map((keyword, index) => (
                  <Chip
                    key={index}
                    label={`#${keyword.word} (${keyword.count})`}
                    color="primary"
                    variant="outlined"
                    onClick={() => {
                      // 키워드로 검색 기능 구현
                    }}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            ) : (
              <Alert severity="info">
                현재 트렌딩 키워드가 없습니다.
              </Alert>
            )}
          </Box>
        </TabPanel>

        {/* 북마크 탭 */}
        <TabPanel value={tabValue} index={3}>
          <Box sx={{ p: 2 }}>
            {bookmarks.size > 0 ? (
              <Typography variant="body2">
                북마크된 뉴스: {bookmarks.size}개
              </Typography>
            ) : (
              <Alert severity="info">
                북마크된 뉴스가 없습니다. 뉴스 목록에서 북마크 아이콘을 클릭하여 추가하세요.
              </Alert>
            )}
          </Box>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default News;