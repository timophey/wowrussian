import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  InputAdornment,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack,
  Search,
  Clear,
  ExpandMore,
  Assessment,
  CheckCircle,
  Warning,
  MenuBook,
  Visibility,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { singleApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

function SinglePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  const [showResults, setShowResults] = useState(false);
  
  // Table sorting and filtering
  const [order, setOrder] = useState('asc');
  const [orderBy, setOrderBy] = useState('word');
  const [filterWord, setFilterWord] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError(t('home.pleaseEnterUrl'));
      return;
    }
    
    // Ensure URL has protocol
    let fullUrl = url.trim();
    if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
      fullUrl = 'https://' + fullUrl;
    }
    
    setError('');
    setLoading(true);
    setShowResults(false);
    
    try {
      const response = await singleApi.check(fullUrl);
      if (response.data.success) {
        setResults(response.data.data);
        setShowResults(true);
      } else {
        setError(response.data.detail || t('errors.failedToLoad'));
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('errors.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };
  
  const handleClear = () => {
    setUrl('');
    setResults(null);
    setShowResults(false);
    setError('');
    setFilterWord('');
  };
  
  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Helper to get sort value for recommendation column
  const getRecommendationSortValue = (wordData) => {
    if (wordData.law_article) return wordData.law_article.toLowerCase();
    if (wordData.recommendation) return wordData.recommendation.toLowerCase();
    return '';
  };
  
  // Get data from results
  const data = results || {};
  const stats = data.statistics || {};
  const summary = data.summary || {};
  const checks = data.checks || {};
  const allWords = data.all_words || [];
  const dictionaries = data.dictionaries_used || [];
  const sourceInfo = data.source_info;
  
  // Filter words
  const filteredWords = allWords.filter(wordData => 
    wordData.word.toLowerCase().includes(filterWord.toLowerCase())
  );
  
  // Sort words
  const sortedWords = [...filteredWords].sort((a, b) => {
    let aVal, bVal;
    
    if (orderBy === 'word') {
      aVal = (a.word || '').toLowerCase();
      bVal = (b.word || '').toLowerCase();
    } else if (orderBy === 'count') {
      aVal = parseInt(a.count) || 0;
      bVal = parseInt(b.count) || 0;
    } else if (orderBy === 'status') {
      aVal = (a.status || '').toLowerCase();
      bVal = (b.status || '').toLowerCase();
    } else if (orderBy === 'categories') {
      aVal = (a.categories || []).join(', ').toLowerCase();
      bVal = (b.categories || []).join(', ').toLowerCase();
    } else if (orderBy === 'recommendation') {
      aVal = getRecommendationSortValue(a);
      bVal = getRecommendationSortValue(b);
    } else {
      aVal = a[orderBy] || '';
      bVal = b[orderBy] || '';
    }
    
    if (order === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });
  
  const getStatusBadge = (status) => {
    const statusMap = {
      ok: { color: 'success', label: '✅ OK' },
      prohibited: { color: 'error', label: '⛔ Запрещено' },
      foreign: { color: 'warning', label: '🌐 Иностранное' },
      normative_violation: { color: 'info', label: '📚 Нарушение' },
    };
    const s = statusMap[status] || { color: 'default', label: status };
    return <Chip label={s.label} color={s.color} size="small" />;
  };
  
  const getRiskLabel = (risk) => {
    const labels = {
      low: 'Низкий',
      medium: 'Средний',
      high: 'Высокий',
    };
    return labels[risk] || risk;
  };
  
  const getRiskColor = (risk) => {
    const colors = {
      low: 'success',
      medium: 'warning',
      high: 'error',
    };
    return colors[risk] || 'default';
  };
  
  const downloadReport = () => {
    if (!results) return;
    
    const reportFormat = 'json';
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `fz168-report-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/')}
          variant="outlined"
        >
          {t('single.back')}
        </Button>
        <Typography variant="h4">
          {t('single.title')}
        </Typography>
      </Box>
      
      {/* URL Input Form */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          {t('single.urlLabel')}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {t('single.subtitle')}
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label={t('single.urlLabel')}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t('single.urlPlaceholder')}
            disabled={loading}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
              endAdornment: url && (
                <InputAdornment position="end">
                  <IconButton onClick={() => setUrl('')} edge="end" size="small">
                    <Clear />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          
          <Box display="flex" gap={2}>
            <Button
              type="submit"
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} /> : <Search />}
              disabled={loading}
            >
              {loading ? t('single.analyzing') : t('single.analyzeButton')}
            </Button>
            <Button
              variant="outlined"
              startIcon={<Clear />}
              onClick={handleClear}
              disabled={loading}
            >
              {t('single.clear')}
            </Button>
            {results && (
              <Button
                variant="outlined"
                startIcon={<Visibility />}
                onClick={downloadReport}
                sx={{ ml: 'auto' }}
              >
                {t('single.downloadJson')}
              </Button>
            )}
          </Box>
        </form>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
      
      {/* Results Section */}
      {showResults && results && (
        <>
          {/* Source Info */}
          {sourceInfo && (
            <Alert severity="info" sx={{ mb: 3 }}>
              <strong>{t('single.sourceInfo')}:</strong> {sourceInfo.type === 'url' ? (
                <span>
                  URL: <a href={sourceInfo.url} target="_blank" rel="noopener noreferrer">{sourceInfo.url}</a>
                  <br />
                  {t('single.totalWords')}: {sourceInfo.chars_extracted.toLocaleString()} | {t('single.uniqueWords')}: {sourceInfo.words_extracted.toLocaleString()}
                </span>
              ) : (
                <span>{sourceInfo.type}</span>
              )}
            </Alert>
          )}
          
          {/* Statistics Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4">{stats.total_words?.toLocaleString() || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('single.totalWords')}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4">{stats.unique_words?.toLocaleString() || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('single.uniqueWords')}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color={getRiskColor(summary.risk_level)}>
                    {getRiskLabel(summary.risk_level)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('single.riskLevel')}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4">{summary.violation_count || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('single.violations')}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          {/* Status Summary */}
          {allWords.length > 0 && (
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                {t('single.statusSummary')}
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={2}>
                {Object.entries(
                  allWords.reduce((acc, w) => {
                    acc[w.status] = (acc[w.status] || 0) + 1;
                    return acc;
                  }, {})
                ).map(([status, count]) => (
                  <Chip
                    key={status}
                    label={`${getStatusBadge(status).props.label}: ${count.toLocaleString()}`}
                    variant="outlined"
                  />
                ))}
              </Box>
            </Paper>
          )}
          
          {/* Words Table */}
          {allWords.length > 0 && (
            <Paper sx={{ mb: 3 }}>
              <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="subtitle1">
                  {t('single.allWords')} ({filteredWords.length})
                </Typography>
                <TextField
                  size="small"
                  placeholder={t('single.wordFilterPlaceholder')}
                  value={filterWord}
                  onChange={(e) => setFilterWord(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search />
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>
              
              <TableContainer sx={{ maxHeight: 500 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'word'}
                          direction={orderBy === 'word' ? order : 'asc'}
                          onClick={() => handleSort('word')}
                        >
                          {t('single.word')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel
                          active={orderBy === 'count'}
                          direction={orderBy === 'count' ? order : 'asc'}
                          onClick={() => handleSort('count')}
                        >
                          {t('single.count')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'status'}
                          direction={orderBy === 'status' ? order : 'asc'}
                          onClick={() => handleSort('status')}
                        >
                          {t('single.status')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'categories'}
                          direction={orderBy === 'categories' ? order : 'asc'}
                          onClick={() => handleSort('categories')}
                        >
                          {t('single.categories')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'recommendation'}
                          direction={orderBy === 'recommendation' ? order : 'asc'}
                          onClick={() => handleSort('recommendation')}
                        >
                          {t('single.recommendation')}
                        </TableSortLabel>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedWords.map((wordData, index) => (
                      <TableRow key={index} hover>
                        <TableCell>{wordData.word}</TableCell>
                        <TableCell align="right">{wordData.count || 1}</TableCell>
                        <TableCell>{getStatusBadge(wordData.status)}</TableCell>
                        <TableCell>
                          {wordData.categories && wordData.categories.length > 0 ? (
                            <Box display="flex" flexWrap="wrap" gap={0.5}>
                              {wordData.categories.map((cat, idx) => (
                                <Chip key={idx} label={cat} size="small" variant="outlined" />
                              ))}
                            </Box>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell>
                          {wordData.law_article && (
                            <Typography variant="body2" color="error">
                              {wordData.law_article}
                            </Typography>
                          )}
                          {wordData.recommendation && !wordData.law_article && (
                            <Typography variant="body2" color="warning.main">
                              {wordData.recommendation}
                            </Typography>
                          )}
                          {wordData.status === 'ok' && !wordData.law_article && !wordData.recommendation && (
                            <Typography variant="body2" color="success.main">
                              ✅ {t('page.detectedForeignWords') === 'Detected Foreign Words' ? 'Complies' : 'Соответствует нормам'}
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}
          
          {/* Accordions for detailed info */}
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box display="flex" alignItems="center" gap={1}>
                <Assessment />
                <Typography>{t('single.summaryTitle')}</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {Object.keys(summary).length > 0 ? (
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                  {JSON.stringify(summary, null, 2)}
                </pre>
              ) : (
                <Typography color="text.secondary">{t('single.noData')}</Typography>
              )}
            </AccordionDetails>
          </Accordion>
          
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box display="flex" alignItems="center" gap={1}>
                <CheckCircle />
                <Typography>{t('single.checksTitle')}</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {checks.prohibited_words && checks.prohibited_words.length > 0 ? (
                <Paper variant="outlined" sx={{ mb: 2, borderColor: 'error.main' }}>
                  <Paper sx={{ bgcolor: 'error.main', color: 'white', p: 1 }}>
                    <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      ⚠️ {t('fz168.prohibitedWords', { defaultValue: 'Запрещенные слова' })} ({checks.prohibited_words.length})
                    </Typography>
                  </Paper>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>{t('single.word')}</TableCell>
                          <TableCell align="right">{t('single.count')}</TableCell>
                          <TableCell>{t('fz168.lawArticle')}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {checks.prohibited_words.map((item, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell><strong>{item.word}</strong></TableCell>
                            <TableCell align="right">{item.count}</TableCell>
                            <TableCell>{item.law_article || '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              ) : null}
              
              {checks.foreign_words && checks.foreign_words.length > 0 ? (
                <Paper variant="outlined" sx={{ mb: 2, borderColor: 'warning.main' }}>
                  <Paper sx={{ bgcolor: 'warning.main', color: 'text.primary', p: 1 }}>
                    <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      🌐 {t('fz168.foreignWords', { defaultValue: 'Иностранные слова' })} ({checks.foreign_words.length})
                    </Typography>
                  </Paper>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>{t('single.word')}</TableCell>
                          <TableCell align="right">{t('single.count')}</TableCell>
                          <TableCell>{t('single.recommendation')}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {checks.foreign_words.map((item, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell>{item.word}</TableCell>
                            <TableCell align="right">{item.count}</TableCell>
                            <TableCell>{item.recommendation || '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              ) : null}
              
              {checks.normative_violations && checks.normative_violations.length > 0 ? (
                <Paper variant="outlined" sx={{ mb: 2, borderColor: 'info.main' }}>
                  <Paper sx={{ bgcolor: 'info.main', color: 'white', p: 1 }}>
                    <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      📚 {t('fz168.normativeViolations', { defaultValue: 'Нарушения норм' })} ({checks.normative_violations.length})
                    </Typography>
                  </Paper>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>{t('single.word')}</TableCell>
                          <TableCell align="right">{t('single.count')}</TableCell>
                          <TableCell>{t('fz168.explanation')}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {checks.normative_violations.map((item, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell>{item.word}</TableCell>
                            <TableCell align="right">{item.count}</TableCell>
                            <TableCell>{item.issue || item.explanation || '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              ) : null}
              
              {checks.recommendations && checks.recommendations.length > 0 ? (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    💡 {t('fz168.recommendations', { defaultValue: 'Рекомендации' })}
                  </Typography>
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    {checks.recommendations.map((rec, idx) => (
                      <li key={idx}><Typography variant="body2">{rec}</Typography></li>
                    ))}
                  </Box>
                </Paper>
              ) : null}
              
              {(!checks.prohibited_words || checks.prohibited_words.length === 0) &&
               (!checks.foreign_words || checks.foreign_words.length === 0) &&
               (!checks.normative_violations || checks.normative_violations.length === 0) &&
               (!checks.recommendations || checks.recommendations.length === 0) && (
                <Typography color="text.secondary">{t('single.noData')}</Typography>
              )}
            </AccordionDetails>
          </Accordion>
          
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box display="flex" alignItems="center" gap={1}>
                <MenuBook />
                <Typography>{t('single.statisticsTitle')}</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {JSON.stringify(stats, null, 2)}
              </pre>
            </AccordionDetails>
          </Accordion>
          
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box display="flex" alignItems="center" gap={1}>
                <Warning />
                <Typography>{t('single.dictionariesTitle')}</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {dictionaries.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t('fz168.dictionaryName', { defaultValue: 'Название' })}</TableCell>
                        <TableCell align="right">{t('fz168.wordsCount', { defaultValue: 'Слов' })}</TableCell>
                        <TableCell>{t('fz168.category', { defaultValue: 'Категория' })}</TableCell>
                        <TableCell>{t('fz168.source', { defaultValue: 'Источник' })}</TableCell>
                        <TableCell>{t('fz168.status', { defaultValue: 'Статус' })}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {dictionaries.map((dict, idx) => (
                        <TableRow key={idx} hover>
                          <TableCell>{dict.name || dict.id}</TableCell>
                          <TableCell align="right">{dict.words_count?.toLocaleString() || '-'}</TableCell>
                          <TableCell>{dict.category || dict.category_code || '-'}</TableCell>
                          <TableCell>{dict.source || '-'}</TableCell>
                          <TableCell>
                            <Chip
                              label={dict.status || 'unknown'}
                              size="small"
                              color={dict.status === 'synced' ? 'success' : 'default'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary">{t('single.noData')}</Typography>
              )}
            </AccordionDetails>
          </Accordion>
        </>
      )}
    </Container>
  );
}

export default SinglePage;
