import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  const { id } = useParams();
  const navigate = useNavigate();
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
      const [projectRes, pagesRes, statsRes] = await Promise.all([
        projectApi.get(id),
        pageApi.list(id, { sort_by: sortBy, sort_order: sortOrder }),
        statsApi.get(id),
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
        setError(err.response?.data?.detail || 'Failed to load project');
      }
    } finally {
      fetchInProgress.current = false;
      if (mountedRef.current && currentIdRef.current === id) {
        setLoading(false);
      }
    }
  }, [id, sortBy, sortOrder]);

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
      await projectApi.stop(id);
      // Optimistically update status
      setProject(prev => prev ? { ...prev, status: 'stopped' } : null);
    } catch (err) {
      setError('Failed to stop project');
    }
  };

  const handleStart = async () => {
    try {
      await projectApi.start(id);
      // Optimistically update status to crawling
      setProject(prev => prev ? { ...prev, status: 'crawling' } : null);
      // Clear pages list as they will be re-crawled
      setPages([]);
      setStats({ total_pages: 0, foreign_words_count: 0, unique_foreign_words: 0, foreign_percentage: 0 });
    } catch (err) {
      setError('Failed to start project: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleClear = async () => {
    try {
      await projectApi.clearPages(id);
      // Optimistically clear pages and reset stats
      setPages([]);
      setStats({ total_pages: 0, foreign_words_count: 0, unique_foreign_words: 0, foreign_percentage: 0 });
      setProject(prev => prev ? { ...prev, status: 'pending' } : null);
      setClearDialogOpen(false);
    } catch (err) {
      setError('Failed to clear pages: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleViewPage = async (page) => {
    try {
      const res = await pageApi.get(page.project_id, page.id);
      setPageDetail(res.data);
      setSelectedPage(page);
      setPageDetailOpen(true);
    } catch (err) {
      setError('Failed to load page details');
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'crawling':
        return 'Crawling';
      case 'parsing':
        return 'Parsing';
      case 'analyzing':
        return 'Analyzing';
      case 'completed':
        return 'Completed';
      case 'stopped':
        return 'Stopped';
      case 'failed':
        return 'Failed';
      case 'queued':
        return 'Queued';
      case 'parsed':
        return 'Parsed';
      case 'analyzed':
        return 'Analyzed';
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
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box sx={{ mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/projects')} sx={{ mb: 2 }}>
          Back to Projects
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
            WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
          </Typography>
        </Box>
      </Box>

      {stats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Pages
                </Typography>
                <Typography variant="h4">{stats.total_pages}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Foreign Words
                </Typography>
                <Typography variant="h4">{stats.total_foreign_words}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Unique Foreign
                </Typography>
                <Typography variant="h4">{stats.unique_foreign_words}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Foreign %
                </Typography>
                <Typography variant="h4">{stats.foreign_percentage.toFixed(1)}%</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Pages</Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={handleStart}
            disabled={['crawling', 'parsing', 'analyzing'].includes(project?.status)}
          >
            Start Download
          </Button>
          <Button
            variant="outlined"
            startIcon={<Stop />}
            onClick={handleStop}
            disabled={['completed', 'stopped', 'failed'].includes(project?.status)}
          >
            Stop
          </Button>
          <Button
            variant="outlined"
            startIcon={<Delete />}
            onClick={() => setClearDialogOpen(true)}
            disabled={['crawling', 'parsing', 'analyzing'].includes(project?.status)}
            color="error"
          >
            Clear Pages
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortBy === 'url'}
                  direction={sortBy === 'url' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('url')}
                >
                  URL
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortBy === 'status'}
                  direction={sortBy === 'status' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('status')}
                >
                  Status
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortBy === 'foreign_words_count'}
                  direction={sortBy === 'foreign_words_count' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('foreign_words_count')}
                >
                  Foreign Words
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortBy === 'words_count'}
                  direction={sortBy === 'words_count' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('words_count')}
                >
                  Total Words
                </TableSortLabel>
              </TableCell>
              <TableCell align="center">Actions</TableCell>
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
                  No pages yet
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
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Status: {getStatusLabel(pageDetail.status)}
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Total words: {pageDetail.words_count}
                </Typography>
                <Typography variant="body2">
                  Foreign words: {pageDetail.foreign_words_count}
                </Typography>
              </Box>

              {pageDetail.foreign_words && pageDetail.foreign_words.length > 0 && (
                <>
                  <Typography variant="h6" gutterBottom>
                    Foreign Words Found
                  </Typography>
                  <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Word</TableCell>
                          <TableCell align="right">Count</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {pageDetail.foreign_words.map((fw, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{fw.word}</TableCell>
                            <TableCell align="right">{fw.count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              )}

              {pageDetail.text_content && (
                <>
                  <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                    Extracted Text
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, maxHeight: 300, overflow: 'auto' }}>
                    <Typography variant="body2" component="pre" style={{ whiteSpace: 'pre-wrap' }}>
                      {pageDetail.text_content.substring(0, 2000)}
                      {pageDetail.text_content.length > 2000 && '... (truncated)'}
                    </Typography>
                  </Paper>
                </>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setPageDetailOpen(false)}>Close</Button>
            </DialogActions>
          </>
        ) : (
          <CircularProgress sx={{ p: 4 }} />
        )}
      </Dialog>

      {/* Clear Pages Confirmation Dialog */}
      <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)}>
        <DialogTitle>Clear All Pages?</DialogTitle>
        <DialogContent>
          <Typography>
            This will delete all pages, crawl queue, and associated data for this project.
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleClear} color="error" variant="contained">
            Clear All
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ProjectPage;