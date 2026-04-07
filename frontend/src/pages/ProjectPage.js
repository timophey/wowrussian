import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
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
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Link,
  Checkbox,
} from '@mui/material';
import { Visibility, Stop, ArrowBack, PlayArrow, Delete, FileDownload, ExpandMore, List, Add, Close } from '@mui/icons-material';
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

// Memoized word row component with internal selection state
const ForeignWordRow = React.memo(({ word, wordCount, pagesCount, pages, isAlreadyInWhitelist, onToggle, onViewPage }) => {
  const [isSelected, setIsSelected] = useState(false);

  const handleChange = useCallback((e) => {
    const checked = e.target.checked;
    setIsSelected(checked);
    onToggle(word, checked);
  }, [word, onToggle]);

  return (
    <TableRow sx={isAlreadyInWhitelist ? { opacity: 0.6 } : {}}>
      <TableCell padding="checkbox">
        {isAlreadyInWhitelist ? (
          <Chip label="✓" size="small" color="success" variant="filled" />
        ) : (
          <Checkbox
            checked={isSelected}
            onChange={handleChange}
            size="small"
          />
        )}
      </TableCell>
      <TableCell>
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>{word}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {pages && pages.length > 0 ? (
              <Box component="ul" sx={{ m: 0, pl: 2 }}>
                {pages.map((page, pageIndex) => (
                  <Box component="li" key={pageIndex} sx={{ mb: 0.5 }}>
                    <Link
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        onViewPage(page);
                      }}
                      underline="hover"
                    >
                      {page.url}
                    </Link>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No pages found.
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>
      </TableCell>
      <TableCell align="right">{wordCount}</TableCell>
      <TableCell>
        <Chip
          label={pagesCount}
          size="small"
          variant="outlined"
        />
      </TableCell>
    </TableRow>
  );
});

function ProjectPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const { isAuthenticated, user } = useAuth();
  const isAdmin = user?.role === 'admin';

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
  const [violationsDialogOpen, setViolationsDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportJob, setExportJob] = useState(null); // Current export job being tracked
  const [exportProgress, setExportProgress] = useState(0); // 0-100
  const [exportStatus, setExportStatus] = useState(''); // pending, processing, completed, failed
  const [exportError, setExportError] = useState('');
  const [pageDetailSource, setPageDetailSource] = useState(null); // 'pages' | 'violations' | null
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [uniqueWordsDialogOpen, setUniqueWordsDialogOpen] = useState(false);
  const [uniqueForeignWords, setUniqueForeignWords] = useState([]);
  const [uniqueWordsLoading, setUniqueWordsLoading] = useState(false);
  const [uniqueWordsSortBy, setUniqueWordsSortBy] = useState('total_count');
  const [uniqueWordsSortOrder, setUniqueWordsSortOrder] = useState('desc');
  const [whitelistDialogOpen, setWhitelistDialogOpen] = useState(false);
  const [whitelistWords, setWhitelistWords] = useState([]);
  const [whitelistLoading, setWhitelistLoading] = useState(false);
  const [selectedCount, setSelectedCount] = useState(0);

  // Ref for tracking selected words (managed by child components)
  const selectedWordsRef = useRef(new Set());

  // Ref for whitelist words to avoid recreating callbacks
  const whitelistWordsRef = useRef(new Set());

  // Memoized Set for O(1) whitelist lookups (for UI rendering only)
  // Note: whitelist words are stored in lowercase, so we compare lowercase
  const whitelistWordsSet = useMemo(
    () => new Set(whitelistWords.map(w => w.word.toLowerCase())),
    [whitelistWords]
  );

  // Update ref when whitelistWords changes
  useEffect(() => {
    whitelistWordsRef.current = new Set(whitelistWords.map(w => w.word.toLowerCase()));
  }, [whitelistWords]);

  // Memoized checkbox handler - uses ref to avoid recreating callback
  const handleWordSelection = useCallback((word, isChecked) => {
    // Don't allow selecting words already in whitelist (case-insensitive comparison)
    if (whitelistWordsRef.current.has(word.toLowerCase())) return;
    
    // Update the selected words ref directly (no state update = no re-render of other rows)
    if (isChecked) {
      selectedWordsRef.current.add(word);
    } else {
      selectedWordsRef.current.delete(word);
    }
    // Update the count state for the button (only this component re-renders)
    setSelectedCount(selectedWordsRef.current.size);
  }, []);

  const { messages, isConnected } = useWebSocket(id);

  // Refs to track state and debounce
  const fetchInProgress = useRef(false);
  const debounceTimer = useRef(null);
  const mountedRef = useRef(true);
  const currentIdRef = useRef(id);
  const lastProcessedMessageCount = useRef(0);
  const downloadTriggeredForJobId = useRef(null); // Track which export job already triggered download

  // Keep current id ref updated
  useEffect(() => {
    currentIdRef.current = id;
  }, [id]);

  // Full fetch for initial load - fetches everything
  const fetchProjectFull = useCallback(async () => {
    if (fetchInProgress.current) {
      return; // Prevent concurrent fetches
    }

    fetchInProgress.current = true;
    try {
      // Use guest session token if not authenticated
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const [projectRes, pagesRes, statsRes, whitelistRes] = await Promise.all([
        projectApi.get(id, guestToken),
        pageApi.list(id, { sort_by: sortBy, sort_order: sortOrder, guest_session_token: guestToken }),
        statsApi.get(id, guestToken),
        projectApi.getWhitelist(id, guestToken),
      ]);
      // Only update state if this is still the current project
      if (mountedRef.current && currentIdRef.current === id) {
        setProject(projectRes.data);
        setPages(pagesRes.data);
        setStats(statsRes.data);
        setWhitelistWords(whitelistRes.data || []);
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

  // Lightweight fetch for pages only - stats come via WebSocket
  const fetchPagesOnly = useCallback(async () => {
    if (fetchInProgress.current) {
      return; // Prevent concurrent fetches
    }

    fetchInProgress.current = true;
    try {
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const pagesRes = await pageApi.list(id, { sort_by: sortBy, sort_order: sortOrder, guest_session_token: guestToken });
      // Only update state if this is still the current project
      if (mountedRef.current && currentIdRef.current === id) {
        setPages(pagesRes.data);
        setError(''); // Clear any previous errors on success
      }
    } catch (err) {
      if (mountedRef.current && currentIdRef.current === id) {
        setError(err.response?.data?.detail || t('errors.failedToLoad'));
      }
    } finally {
      fetchInProgress.current = false;
    }
  }, [id, sortBy, sortOrder, isAuthenticated]);

  // Initial full fetch on mount or when sort changes
  useEffect(() => {
    setLoading(true);
    fetchProjectFull();
  }, [fetchProjectFull]);

  // Handle WebSocket messages with incremental updates
  useEffect(() => {
    // Skip if there are no new messages
    if (messages.length <= lastProcessedMessageCount.current) {
      return;
    }
    // Update the count to current length
    lastProcessedMessageCount.current = messages.length;

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
       }
       else if (lastMessage.event === 'page_analyzed') {
         const { page_id, url, words_count, foreign_words_count, fz168_summary, fz168_statistics, fz168_checks, fz168_dictionaries, fz168_raw_response } = lastMessage.data;
         // Update page with analysis results including fz168 data for violations display
         setPages(prev => prev.map(page =>
           page.id === page_id
             ? {
                 ...page,
                 status: 'analyzed',
                 words_count,
                 foreign_words_count,
                 fz168_summary: fz168_summary || page.fz168_summary,
                 fz168_statistics: fz168_statistics || page.fz168_statistics,
                 fz168_checks: fz168_checks || page.fz168_checks,
                 fz168_dictionaries: fz168_dictionaries || page.fz168_dictionaries,
                 fz168_raw_response: fz168_raw_response || page.fz168_raw_response
               }
             : page
         ));
       }
       else if (lastMessage.event === 'stats_update') {
         // Handle comprehensive stats update from WebSocket
         const statsData = lastMessage.data;
         setStats(statsData);
       }
       else if (lastMessage.event === 'project_completed') {
         setProject(prev => prev ? { ...prev, status: 'completed' } : null);
       }
       else if (lastMessage.event === 'error') {
         setError(lastMessage.data.message);
       }
        // Handle export job updates
        else if (lastMessage.event && lastMessage.event.startsWith('export_')) {
          const exportEvent = lastMessage.event.replace('export_', '');
          const jobData = lastMessage.data;
          const jobId = lastMessage.job_id;

          if (exportEvent === 'progress') {
            setExportProgress(jobData.progress || 0);
            setExportStatus('processing');
          } else if (exportEvent === 'completed') {
            setExportStatus('completed');
            setExportProgress(100);
            // Merge job_id into jobData
            setExportJob({ ...jobData, job_id: jobId });
            setExportLoading(false);
            // Auto-download the file (only once per job)
            if (downloadTriggeredForJobId.current !== jobId) {
              downloadTriggeredForJobId.current = jobId;
              const guestToken = getGuestToken();
              downloadExportFile(jobId, guestToken);
            }
          } else if (exportEvent === 'failed') {
            setExportStatus('failed');
            setExportError(jobData.error || 'Export failed');
            setExportLoading(false);
          } else if (exportEvent === 'cancelled') {
            setExportStatus('failed');
            setExportError('Export was cancelled');
            setExportLoading(false);
          }
        }
     }

    // No longer need debounced fetchProject - stats come via WebSocket
    // Only fetch on initial load or when sort changes

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [messages, id]);

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

  const handleResume = async () => {
    try {
      const guestToken = getGuestToken();
      await projectApi.resume(id, guestToken);
      // Optimistically update status to crawling
      setProject(prev => prev ? { ...prev, status: 'crawling' } : null);
      // Don't clear pages - we're resuming from where we left off
    } catch (err) {
      setError(t('errors.failedToResumeProject') + ': ' + (err.response?.data?.detail || err.message));
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

  const handleExportProject = async () => {
    setExportDialogOpen(true);
  };

   const executeExportProject = async () => {
     setExportDialogOpen(false);
     setExportLoading(true);
     setExportError('');
     setExportJob(null);
     setExportProgress(0);
     setExportStatus('pending');
     downloadTriggeredForJobId.current = null; // Reset download tracker for new export

      try {
        const guestToken = getGuestToken();
        const currentLanguage = i18n.language || 'ru';
        const clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

        // Start async export job
        const response = await projectApi.startAsyncExport(id, currentLanguage, guestToken, clientTimezone);
       const job = response.data;
       setExportJob(job);
       setExportStatus('processing');

       // WebSocket will handle updates automatically via the messages effect below
       // No need for polling anymore

     } catch (error) {
       console.error('Failed to start export job:', error);
       setExportError(error.response?.data?.detail || error.message || 'Failed to start export');
       setExportLoading(false);
     }
   };

   const cancelExportProject = async () => {
     if (!exportJob) return;

     try {
       const guestToken = getGuestToken();
       await projectApi.cancelExportJob(exportJob.job_id, guestToken);
       // The WebSocket will receive the cancellation event and update the UI
     } catch (error) {
       console.error('Failed to cancel export job:', error);
       setExportError(error.response?.data?.detail || error.message || 'Failed to cancel export');
     }
   };



  const downloadExportFile = async (jobId, guestToken) => {
    try {
      const response = await projectApi.downloadExportFile(jobId, guestToken);
      // Use the Blob directly from the response
      const blob = response.data;
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      
      // Extract filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition'];
      let filename = `project_words_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      alert('Export completed but download failed: ' + (error.message || error));
      setExportLoading(false);
    }
  };

  const handleViewPage = async (page) => {
    try {
      const guestToken = getGuestToken();
      const res = await pageApi.get(page.project_id, page.id, guestToken);
      setPageDetail(res.data);
      setSelectedPage(page);
      setPageDetailSource('pages');
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

  const getPagesWithViolations = () => {
    if (!pages) return [];
    return pages
      .filter(page => {
        const summary = page.fz168_summary;
        return summary && summary.violation_count && summary.violation_count > 0;
      })
      .map(page => ({
        id: page.id,
        url: page.url,
        risk_level: page.fz168_summary?.risk_level || 'low',
        violation_count: page.fz168_summary?.violation_count || 0,
        status: page.status
      }))
      .sort((a, b) => b.violation_count - a.violation_count); // Sort by violations descending
  };

  const handleViewPageFromViolations = async (page) => {
    try {
      const guestToken = getGuestToken();
      const res = await pageApi.get(page.project_id || id, page.id, guestToken);
      setPageDetail(res.data);
      setSelectedPage(page);
      setPageDetailSource('violations');
      setPageDetailOpen(true);
      // Keep violations dialog open - don't close it here
    } catch (err) {
      setError(t('errors.failedToLoadPageDetails'));
    }
  };

  const handleOpenUniqueWordsDialog = async () => {
    setUniqueWordsLoading(true);
    try {
      const guestToken = getGuestToken();
      const res = await statsApi.getUniqueForeignWords(id, guestToken);
      setUniqueForeignWords(res.data.words || []);
    } catch (err) {
      console.error('Failed to fetch unique foreign words:', err);
      setError(t('errors.failedToLoad'));
    } finally {
      setUniqueWordsLoading(false);
    }
    setUniqueWordsDialogOpen(true);
  };

  // Whitelist management functions
  const handleOpenWhitelistDialog = async () => {
    setWhitelistLoading(true);
    try {
      const guestToken = getGuestToken();
      const res = await projectApi.getWhitelist(id, guestToken);
      setWhitelistWords(res.data || []);
    } catch (err) {
      console.error('Failed to fetch whitelist words:', err);
      setError(t('errors.failedToLoad'));
    } finally {
      setWhitelistLoading(false);
    }
    setWhitelistDialogOpen(true);
  };

  const handleAddToWhitelist = async (words) => {
    try {
      const guestToken = getGuestToken();
      const wordsArray = Array.isArray(words) ? words : [words];
      const res = await projectApi.addToWhitelist(id, wordsArray, guestToken);
      // Update the whitelist state with the new words
      setWhitelistWords(prev => [...prev, ...(res.data || [])]);
    } catch (err) {
      console.error('Failed to add words to whitelist:', err);
      setError(t('errors.failedToUpdate'));
    }
  };

  const handleRemoveFromWhitelist = async (wordId) => {
    try {
      const guestToken = getGuestToken();
      await projectApi.removeFromWhitelist(id, wordId, guestToken);
      // Remove the word from the state
      setWhitelistWords(prev => prev.filter(w => w.id !== wordId));
    } catch (err) {
      console.error('Failed to remove word from whitelist:', err);
      setError(t('errors.failedToUpdate'));
    }
  };

  const handleAddSelectedWordsToWhitelist = async () => {
    const selectedWords = Array.from(selectedWordsRef.current);
    if (selectedWords.length === 0) return;
    // Filter out words that are already in the whitelist (case-insensitive comparison)
    const newWords = selectedWords.filter(word => !whitelistWordsRef.current.has(word.toLowerCase()));
    if (newWords.length === 0) return;
    await handleAddToWhitelist(newWords);
    // Clear the selected words ref
    selectedWordsRef.current.clear();
    setSelectedCount(0);
    // Refresh the whitelist from server to update the UI
    try {
      const guestToken = getGuestToken();
      const res = await projectApi.getWhitelist(id, guestToken);
      setWhitelistWords(res.data || []);
    } catch (err) {
      console.error('Failed to refresh whitelist:', err);
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
            <Card
              data-block="stat-card-foreign-words-combined"
              sx={{
                height: '100%',
                cursor: uniqueWordsLoading ? 'default' : 'pointer',
                '&:hover': uniqueWordsLoading ? {} : {
                  bgcolor: 'action.hover'
                },
                opacity: uniqueWordsLoading ? 0.7 : 1,
                position: 'relative'
              }}
              onClick={uniqueWordsLoading ? undefined : handleOpenUniqueWordsDialog}
            >
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.foreignWords')}
                </Typography>
                <Typography variant="h4">{stats.total_foreign_words}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('project.unique')}: {stats.unique_foreign_words}
                </Typography>
                {uniqueWordsLoading && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: 'rgba(255, 255, 255, 0.7)'
                    }}
                  >
                    <CircularProgress size={24} />
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card
              data-block="stat-card-violations"
              sx={{
                height: '100%',
                cursor: 'pointer',
                '&:hover': {
                  bgcolor: 'action.hover'
                }
              }}
              onClick={() => setViolationsDialogOpen(true)}
            >
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.violations')}
                </Typography>
                <Typography variant="h4" color="error">{stats.total_violations || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card
              data-block="stat-card-whitelist"
              sx={{
                height: '100%',
                cursor: 'pointer',
                '&:hover': {
                  bgcolor: 'action.hover'
                }
              }}
              onClick={handleOpenWhitelistDialog}
            >
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {t('project.whitelistTitle', 'Whitelist')}
                </Typography>
                <Typography variant="h4">{whitelistWords.length || 0}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('project.whitelistWords', 'words')}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12}>
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

      <Box data-block="project-actions" display="flex" flexDirection="column" gap={2} mb={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h5">{t('project.pages')}</Typography>
          <Box data-block="action-buttons" display="flex" gap={1}>
            <Button
              data-block="start-download-button"
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleStart}
              disabled={['crawling', 'parsing', 'analyzing'].includes(project?.status) || ['stopped', 'failed'].includes(project?.status)}
            >
              {t('project.startDownload')}
            </Button>
            {['stopped', 'failed'].includes(project?.status) && (
              <Button
                data-block="resume-button"
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleResume}
                color="warning"
              >
                {t('project.resume', 'Resume')}
              </Button>
            )}
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
            <Button
              data-block="export-project-xlsx-button"
              variant="outlined"
              startIcon={exportLoading ? <CircularProgress size={20} /> : <FileDownload />}
              onClick={handleExportProject}
              disabled={pages.length === 0 || exportLoading}
              sx={{ minWidth: 180 }}
            >
              {exportLoading 
                ? `${t('project.exportXLSX', 'Экспорт XLSX')} (${exportProgress}%)`
                : t('project.exportXLSX', 'Экспорт XLSX')
              }
            </Button>
          </Box>
        </Box>
        {exportLoading && (
          <LinearProgress 
            variant="determinate" 
            value={exportProgress} 
            sx={{ width: '100%' }}
          />
        )}
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
                  <a
                    href={page.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: 'inherit',
                      textDecoration: 'none',
                      display: 'block',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                    title={page.url}
                  >
                    {page.url}
                  </a>
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
      <Dialog
        open={pageDetailOpen}
        onClose={() => {
          setPageDetailOpen(false);
          // Return to violations dialog if that's where we came from
          if (pageDetailSource === 'violations') {
            setViolationsDialogOpen(true);
          }
          setPageDetailSource(null);
        }}
        maxWidth="md"
        fullWidth
      >
        {pageDetail ? (
          <>
            <DialogTitle>{selectedPage?.url}</DialogTitle>
            <DialogContent>
              {pageDetail.fz168_raw_response?.data ? (
                <AnalysisResults results={pageDetail.fz168_raw_response.data} pageUrl={selectedPage?.url} isAdmin={isAdmin} />
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

      {/* Violations Details Dialog */}
      <Dialog open={violationsDialogOpen} onClose={() => setViolationsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('violationsDialog.title')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('violationsDialog.description')}
          </Typography>
          
          {pages.length === 0 ? (
            <Alert severity="info">{t('violationsDialog.noData')}</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('violationsDialog.pageUrl')}</TableCell>
                    <TableCell align="center">{t('violationsDialog.riskLevel')}</TableCell>
                    <TableCell align="right">{t('violationsDialog.violations')}</TableCell>
                    <TableCell align="center">{t('violationsDialog.actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {getPagesWithViolations().length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">
                          {t('violationsDialog.noViolations')}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    getPagesWithViolations().map((page) => (
                      <TableRow key={page.id} hover>
                        <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          <a
                            href={page.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: 'inherit',
                              textDecoration: 'none',
                              display: 'block',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                            title={page.url}
                          >
                            {page.url}
                          </a>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={t(`project.riskLevels.${page.risk_level}`)}
                            size="small"
                            color={
                              page.risk_level === 'high' ? 'error' :
                              page.risk_level === 'medium' ? 'warning' : 'success'
                            }
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography color="error" fontWeight="bold">
                            {page.violation_count}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <IconButton
                            size="small"
                            onClick={() => handleViewPageFromViolations(page)}
                            title={t('violationsDialog.viewFullAnalysis')}
                          >
                            <Visibility />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViolationsDialogOpen(false)}>
            {t('dialogs.close')}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Export Project Confirmation Dialog */}
      <Dialog open={exportDialogOpen} onClose={() => !exportLoading && setExportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {exportStatus === 'completed' ? t('project.exportComplete') : t('project.exportXLSX')}
        </DialogTitle>
        <DialogContent>
          {exportError ? (
            <Alert severity="error" sx={{ mt: 2 }}>
              {exportError}
            </Alert>
          ) : exportStatus === 'processing' || exportStatus === 'pending' ? (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t('project.exportProgress', 'Processing export... This may take several minutes for large projects.')}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
                <CircularProgress variant="determinate" value={exportProgress} sx={{ mr: 2 }} />
                <Typography variant="body1" fontWeight="bold">
                  {exportProgress}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={exportProgress} sx={{ mt: 1 }} />
              {exportJob?.total_words && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                  {t('project.exportWordCount', 'Processing {{count}} words', { count: exportJob.total_words })}
                </Typography>
              )}
            </Box>
          ) : exportStatus === 'completed' ? (
            <Alert severity="success" sx={{ mt: 2 }}>
              {t('project.exportReady', 'Export ready! Your download will start automatically.')}
            </Alert>
          ) : (
            <Typography sx={{ mt: 2 }}>
              {t('project.exportConfirmMessage', 'Export all analysis results from all pages to an Excel file? This may take some time.')}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          {exportStatus === 'completed' ? (
            <>
              <Button onClick={() => setExportDialogOpen(false)}>
                {t('dialogs.close')}
              </Button>
              <Button
                onClick={() => {
                  if (exportJob) {
                    const jobId = exportJob.job_id;
                    // Only download if not already triggered for this job
                    if (downloadTriggeredForJobId.current !== jobId) {
                      downloadTriggeredForJobId.current = jobId;
                      downloadExportFile(jobId, getGuestToken());
                    }
                  }
                }}
                variant="contained"
                color="primary"
                startIcon={<FileDownload />}
              >
                {t('project.download')}
              </Button>
            </>
          ) : exportStatus === 'failed' ? (
            <Button onClick={() => setExportDialogOpen(false)} variant="contained">
              {t('dialogs.close')}
            </Button>
           ) : exportStatus === 'processing' ? (
             <>
               <Button 
                 onClick={cancelExportProject} 
                 disabled={!exportLoading}
                 color="error"
               >
                 {t('project.cancelExport', 'Cancel Export')}
               </Button>
               <Button onClick={() => setExportDialogOpen(false)} disabled={exportLoading}>
                 {t('dialogs.close')}
               </Button>
             </>
           ) : (
             <>
               <Button onClick={() => setExportDialogOpen(false)}>
                 {t('dialogs.cancel')}
               </Button>
               <Button
                 onClick={executeExportProject}
                 variant="contained"
                 color="primary"
                 disabled={exportLoading}
               >
                 {exportLoading ? <CircularProgress size={24} /> : t('project.export')}
               </Button>
             </>
           )}
        </DialogActions>
      </Dialog>

      {/* Unique Foreign Words Dialog */}
      <Dialog
        open={uniqueWordsDialogOpen}
        onClose={() => setUniqueWordsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {t('project.uniqueForeignWords', 'Unique Foreign Words')} ({uniqueForeignWords.length})
        </DialogTitle>
        <DialogContent>
          {uniqueWordsLoading ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : uniqueForeignWords.length === 0 ? (
            <Alert severity="info">
              {t('project.noUniqueWords', 'No unique foreign words found.')}
            </Alert>
          ) : (
            <>
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={handleAddSelectedWordsToWhitelist}
                  disabled={selectedCount === 0}
                  size="small"
                >
                  {t('project.addToWhitelist', 'Add to Whitelist')} ({selectedCount})
                </Button>
              </Box>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox"></TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={uniqueWordsSortBy === 'word'}
                          direction={uniqueWordsSortBy === 'word' ? uniqueWordsSortOrder : 'asc'}
                          onClick={() => {
                            if (uniqueWordsSortBy === 'word') {
                              setUniqueWordsSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
                            } else {
                              setUniqueWordsSortBy('word');
                              setUniqueWordsSortOrder('asc');
                            }
                          }}
                        >
                          {t('single.word', 'Word')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel
                          active={uniqueWordsSortBy === 'total_count'}
                          direction={uniqueWordsSortBy === 'total_count' ? uniqueWordsSortOrder : 'desc'}
                          onClick={() => {
                            if (uniqueWordsSortBy === 'total_count') {
                              setUniqueWordsSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
                            } else {
                              setUniqueWordsSortBy('total_count');
                              setUniqueWordsSortOrder('desc');
                            }
                          }}
                        >
                          {t('single.count', 'Count')}
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel
                          active={uniqueWordsSortBy === 'pages_count'}
                          direction={uniqueWordsSortBy === 'pages_count' ? uniqueWordsSortOrder : 'desc'}
                          onClick={() => {
                            if (uniqueWordsSortBy === 'pages_count') {
                              setUniqueWordsSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
                            } else {
                              setUniqueWordsSortBy('pages_count');
                              setUniqueWordsSortOrder('desc');
                            }
                          }}
                        >
                          {t('project.pages', 'Pages')}
                        </TableSortLabel>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {[...uniqueForeignWords]
                      .sort((a, b) => {
                        let aVal, bVal;
                        if (uniqueWordsSortBy === 'word') {
                          aVal = a.word.toLowerCase();
                          bVal = b.word.toLowerCase();
                        } else if (uniqueWordsSortBy === 'total_count') {
                          aVal = a.total_count || 0;
                          bVal = b.total_count || 0;
                        } else if (uniqueWordsSortBy === 'pages_count') {
                          aVal = a.pages?.length || 0;
                          bVal = b.pages?.length || 0;
                        } else {
                          return 0;
                        }
                        
                        if (aVal < bVal) return uniqueWordsSortOrder === 'asc' ? -1 : 1;
                        if (aVal > bVal) return uniqueWordsSortOrder === 'asc' ? 1 : -1;
                        return 0;
                      })
                      .map((wordData, index) => (
                      <ForeignWordRow
                        key={wordData.word}
                        word={wordData.word}
                        wordCount={wordData.total_count}
                        pagesCount={wordData.pages?.length || 0}
                        pages={wordData.pages || []}
                        isAlreadyInWhitelist={whitelistWordsSet.has(wordData.word.toLowerCase())}
                        onToggle={handleWordSelection}
                        onViewPage={(page) => handleViewPage({ id: page.id, project_id: id, url: page.url })}
                      />
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUniqueWordsDialogOpen(false)}>
            {t('dialogs.close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Whitelist Management Dialog */}
      <Dialog
        open={whitelistDialogOpen}
        onClose={() => setWhitelistDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {t('project.whitelistTitle', 'Whitelist Words')} ({whitelistWords.length})
        </DialogTitle>
        <DialogContent>
          {whitelistLoading ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : whitelistWords.length === 0 ? (
            <Alert severity="info">
              {t('project.noWhitelistWords', 'No whitelist words added yet. Words added here will be excluded from violations on the next analysis.')}
            </Alert>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>{t('single.word', 'Word')}</TableCell>
                    <TableCell align="right">{t('dialogs.actions', 'Actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {whitelistWords.map((wordData) => (
                    <TableRow key={wordData.id}>
                      <TableCell>
                        <Typography>{wordData.word}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleRemoveFromWhitelist(wordData.id)}
                          title={t('project.removeFromWhitelist', 'Remove from whitelist')}
                        >
                          <Close />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWhitelistDialogOpen(false)}>
            {t('dialogs.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ProjectPage;