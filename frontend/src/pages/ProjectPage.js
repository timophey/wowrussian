import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TableSortLabel,
} from '@mui/material';
import { Visibility, Stop, ArrowBack, PlayArrow, Delete } from '@mui/icons-material';
import { projectApi, pageApi, statsApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../contexts/AuthContext';
import AnalysisResults from '../components/AnalysisResults';

const STATUS_COLORS = {
  pending: 'default',
  crawling: 'warning',
  parsing: 'info',
  parsed: 'info',
  analyzing: 'info',
  analyzed: 'info',
  completed: 'success',
  stopped: 'error',
  failed: 'error',
  queued: 'default',
};

function ProjectPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const { isAuthenticated } = useAuth();

  const navigate = useNavigate();
  
  // Helper to get guest session token when not authenticated
  const getGuestToken = () => {
    return !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
  };
  
  const [project, setProject] = useState(null);
  const [pages, setPages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPage, setSelectedPage] = useState(null);
  const [pageDetailOpen, setPageDetailOpen] = useState(false);
  const [pageDetail, setPageDetail] = useState(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const { messages, isConnected } = useWebSocket(id);

  // Refs to track state and debounce
  const fetchInProgress = useRef(false);
  const debounceTimer = useRef(null);
  const mountedRef = useRef(true);
  const currentIdRef = useRef(id);

  // Keep current id ref updated
  useEffect(() => {
    currentIdRef.current = id;
  }, [id]);

  const fetchProject = useCallback(async () => {
    if (fetchInProgress.current) {
      return; // Prevent concurrent fetches
    }

    fetchInProgress.current = true;
    try {
      // Use guest session token if not authenticated
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const [projectRes, pagesRes, statsRes] = await Promise.all([
        projectApi.get(id, guestToken),
        pageApi.list(id, { sort_by: sortBy, sort_order: sortOrder, guest_session_token: guestToken }),
        statsApi.get(id, guestToken),
      ]);
      // Only update state if this is still the current project
      if (mountedRef.current && currentIdRef.current === id) {
        setProject(projectRes.data);
        setPages(pagesRes.data);
        setStats(statsRes.data);
        setError(''); // Clear any previous errors on success
      }
    } catch (err) {
      if (mountedRef.current && currentIdRef.current === id) {
        setError(err.response?.data?.detail || t('errors.failedToLoad'));
      }
    } finally {
      fetchInProgress.current = false;
      if (mountedRef.current && currentIdRef.current === id) {
        setLoading(false);
      }
    }
  }, [id, sortBy, sortOrder, t, isAuthenticated]);

  useEffect(() => {
    setLoading(true);
    fetchProject();
  }, [fetchProject]);

  // Handle WebSocket messages with incremental updates
  useEffect(() => {
    // Get the latest message
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return;

    // Only process if this is still the current project
    if (currentIdRef.current !== id) {
      return;
    }

    // Clear any pending debounced fetch
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Process message immediately for incremental updates
    if (mountedRef.current) {
      if (lastMessage.event === 'page_crawled') {
        const { page_id, url } = lastMessage.data;
        // Add new page to the list with basic info
        setPages(prev => {
          // Avoid duplicates
          if (prev.some(p => p.id === page_id)) return prev;
          return [...prev, {
            id: page_id,
            project_id: id,
            url: url,
            status: 'parsed', // After crawling, status is parsed
            foreign_words_count: 0,
            words_count: 0
          }];
        });
        // Update stats incrementally
        setStats(prev => prev ? {
          ...prev,
          total_pages: prev.total_pages + 1
        } : null);
      }
      else if (lastMessage.event === 'page_analyzed') {
        const { page_id, url, words_count, foreign_words_count } = lastMessage.data;
        // Update page with analysis results
        setPages(prev => prev.map(page =>
          page.id === page_id
            ? { ...page, status: 'analyzed', words_count, foreign_words_count }
            : page
        ));
        // Update stats
        setStats(prev => prev ? {
          ...prev,
          total_foreign_words: (prev.total_foreign_words || 0) + foreign_words_count
        } : null);
      }
      else if (lastMessage.event === 'project_completed') {
        setProject(prev => prev ? { ...prev, status: 'completed' } : null);
      }
      else if (lastMessage.event === 'error') {
        setError(lastMessage.data.message);
      }
    }

    // Debounce a full sync to ensure consistency (500ms after last message)
    debounceTimer.current = setTimeout(() => {
      if (mountedRef.current && currentIdRef.current === id) {
        fetchProject();
      }
    }, 500);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [messages, fetchProject, id]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  const handleStop = async () => {
    try {
      const guestToken = getGuestToken();
      await projectApi.stop(id, guestToken);
      // Optimistically update status
      setProject(prev => prev ? { ...prev, status: 'stopped' } : null);
    } catch (err) {
      setError(t('errors.failedToStopProject'));
    }
  };

  const handleStart = async () => {
    try {
      const guestToken = getGuestToken();
      await projectApi.start(id, guestToken);
      // Optimistically update status to crawling
      setProject(prev => prev ? { ...prev, status: 'crawling' } : null);
      // Clear pages list as they will be re-crawled
      setPages([]);
      setStats({
        total_pages: 0,
        total_foreign_words: 0,
        unique_foreign_words: 0,
        foreign_percentage: 0,
        risk_level_distribution: { high: 0, medium: 0, low: 0 },
        total_violations: 0
      });
    } catch (err) {
      setError(t('errors.failedToStartProject') + ': ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleClear = async () => {
    try {
      const guestToken = getGuestToken();
      await projectApi.clearPages(id, guestToken);
      // Optimistically clear pages and reset stats
      setPages([]);
      setStats({
        total_pages: 0,
        total_foreign_words: 0,
        unique_foreign_words: 0,
        foreign_percentage: 0,
        risk_level_distribution: { high: 0, medium: 0, low: 0 },
        total_violations: 0
      });
      setProject(prev => prev ? { ...prev, status: 'pending' } : null);
      setClearDialogOpen(false);
    } catch (err) {
      setError(t('errors.failedToClearPages') + ': ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleViewPage = async (page) => {
    try {
      const guestToken = getGuestToken();
      const res = await pageApi.get(page.project_id, page.id, guestToken);
      setPageDetail(res.data);
      setSelectedPage(page);
      setPageDetailOpen(true);
    } catch (err) {
      setError(t('errors.failedToLoadPageDetails'));
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
        return t('status.pending');
      case 'crawling':
        return t('status.crawling');
      case 'parsing':
        return t('status.parsing');
      case 'analyzing':
        return t('status.analyzing');
      case 'completed':
        return t('status.completed');
      case 'stopped':
        return t('status.stopped');
      case 'failed':
        return t('status.failed');
      case 'queued':
        return t('status.queued');
      case 'parsed':
        return t('status.parsed');
      case 'analyzed':
        return t('status.analyzed');
      default:
        return status;
    }
  };

  const handleRequestSort = (field) => {
    let newSortOrder;
    if (sortBy === field) {
      newSortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      newSortOrder = 'asc';
    }
    setSortBy(field);
    setSortOrder(newSortOrder);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 4 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container data-block="project-container" maxWidth="lg" sx={{ mt: 8 }}>
      <Box data-block="project-header" sx={{ mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/projects')} sx={{ mb: 2 }}>
          {t('project.backToProjects')}
        </Button>
        <Typography variant="h4" gutterBottom>
          {project?.domain}
        </Typography>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Chip
            label={getStatusLabel(project?.status)}
            color={STATUS_COLORS[project?.status] || 'default'}
          />
          <Typography variant="body2" color="text.secondary">
            {t('project.websocket')}: {isConnected ? t('project.connected') : t('project.disconnected')}
          </Typography>
        </Box>
      </Box>

      {stats && (
        <Grid data-block="project-stats" container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card data-block="stat-card-total-pages" sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.totalPages')}
                </Typography>
                <Typography variant="h4">{stats.total_pages}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card data-block="stat-card-foreign-words-combined" sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.foreignWords')}
                </Typography>
                <Typography variant="h4">{stats.total_foreign_words}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('project.unique')}: {stats.unique_foreign_words}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card data-block="stat-card-violations" sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.violations')}
                </Typography>
                <Typography variant="h4" color="error">{stats.total_violations || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card data-block="stat-card-risk-level" sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.riskLevel')}
                </Typography>
                <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
                  {stats.risk_level_distribution && Object.entries(stats.risk_level_distribution).map(([level, count]) => (
                    <Chip
                      key={level}
                      label={`${t(`project.riskLevels.${level}`)}: ${count}`}
                      size="small"
                      color={
                        level === 'high' ? 'error' :
                        level === 'medium' ? 'warning' : 'success'
                      }
                      variant={count > 0 ? 'filled' : 'outlined'}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Box data-block="project-actions" display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">{t('project.pages')}</Typography>
        <Box data-block="action-buttons" display="flex" gap={1}>
          <Button
            data-block="start-download-button"
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={handleStart}
            disabled={['crawling', 'parsing', 'analyzing'].includes(project?.status)}
          >
            {t('project.startDownload')}
          </Button>
          <Button
            data-block="stop-button"
            variant="outlined"
            startIcon={<Stop />}
            onClick={handleStop}
            disabled={['completed', 'stopped', 'failed'].includes(project?.status)}
          >
            {t('project.stop')}
          </Button>
          <Button
            data-block="clear-pages-button"
            variant="outlined"
            startIcon={<Delete />}
            onClick={() => setClearDialogOpen(true)}
            disabled={['crawling', 'parsing', 'analyzing'].includes(project?.status)}
            color="error"
          >
            {t('project.clearPages')}
          </Button>
        </Box>
      </Box>

      <TableContainer data-block="pages-table" component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortBy === 'url'}
                  direction={sortBy === 'url' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('url')}
                >
                  {t('project.url')}
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortBy === 'status'}
                  direction={sortBy === 'status' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('status')}
                >
                  {t('project.status')}
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortBy === 'foreign_words_count'}
                  direction={sortBy === 'foreign_words_count' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('foreign_words_count')}
                >
                  {t('project.foreignWords')}
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortBy === 'words_count'}
                  direction={sortBy === 'words_count' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('words_count')}
                >
                  {t('project.totalWords')}
                </TableSortLabel>
              </TableCell>
              <TableCell align="center">{t('project.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pages.map((page) => (
              <TableRow key={page.id}>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {page.url}
                </TableCell>
                <TableCell>
                  <Chip
                    label={getStatusLabel(page.status)}
                    size="small"
                    color={STATUS_COLORS[page.status] || 'default'}
                  />
                </TableCell>
                <TableCell align="right">{page.foreign_words_count || 0}</TableCell>
                <TableCell align="right">{page.words_count || 0}</TableCell>
                <TableCell align="center">
                  <IconButton size="small" onClick={() => handleViewPage(page)}>
                    <Visibility />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {pages.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  {t('page.noForeignWords')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Page Detail Dialog */}
      <Dialog open={pageDetailOpen} onClose={() => setPageDetailOpen(false)} maxWidth="md" fullWidth>
        {pageDetail ? (
          <>
            <DialogTitle>{selectedPage?.url}</DialogTitle>
            <DialogContent>
              {pageDetail.fz168_raw_response?.data ? (
                <AnalysisResults results={pageDetail.fz168_raw_response.data} />
              ) : (
                <Alert severity="warning">
                  {t('page.analysisNotAvailable')}
                </Alert>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setPageDetailOpen(false)}>{t('dialogs.close')}</Button>
            </DialogActions>
          </>
        ) : (
          <CircularProgress sx={{ p: 4 }} />
        )}
      </Dialog>

      {/* Clear Pages Confirmation Dialog */}
      <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)}>
        <DialogTitle>{t('dialogs.clearAllPages')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t('dialogs.clearConfirmation')}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)}>{t('dialogs.cancel')}</Button>
          <Button onClick={handleClear} color="error" variant="contained">
            {t('dialogs.clearAll')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ProjectPage;