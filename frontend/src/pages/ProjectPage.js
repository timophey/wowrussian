import React, { useState, useEffect, useCallback } from 'react';
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
} from '@mui/material';
import { Visibility, Stop, ArrowBack } from '@mui/icons-material';
import { projectApi, pageApi, statsApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const STATUS_COLORS = {
  pending: 'default',
  crawling: 'warning',
  parsing: 'info',
  analyzing: 'info',
  completed: 'success',
  stopped: 'error',
  failed: 'error',
  queued: 'default',
  parsed: 'info',
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

  const { messages, isConnected } = useWebSocket(id);

  const fetchProject = useCallback(async () => {
    try {
      const [projectRes, pagesRes, statsRes] = await Promise.all([
        projectApi.get(id),
        pageApi.list(id),
        statsApi.get(id),
      ]);
      setProject(projectRes.data);
      setPages(pagesRes.data);
      setStats(statsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  // Handle WebSocket messages
  useEffect(() => {
    messages.forEach((msg) => {
      if (msg.event === 'page_crawled' || msg.event === 'page_analyzed') {
        fetchProject();
      }
      if (msg.event === 'project_completed') {
        fetchProject();
      }
      if (msg.event === 'error') {
        setError(msg.data.message);
      }
    });
  }, [messages, fetchProject]);

  const handleStop = async () => {
    try {
      await projectApi.stop(id);
      fetchProject();
    } catch (err) {
      setError('Failed to stop project');
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
        <Button
          variant="outlined"
          startIcon={<Stop />}
          onClick={handleStop}
          disabled={['completed', 'stopped', 'failed'].includes(project?.status)}
        >
          Stop
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>URL</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Foreign Words</TableCell>
              <TableCell align="right">Total Words</TableCell>
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
    </Container>
  );
}

export default ProjectPage;