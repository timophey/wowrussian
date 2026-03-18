import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
} from '@mui/material';
import { ArrowBack, Visibility, Code } from '@mui/icons-material';
import { pageApi } from '../services/api';

function PageDetailPage() {
  const { projectId, pageId } = useParams();
  const navigate = useNavigate();
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0);
  const [htmlDialogOpen, setHtmlDialogOpen] = useState(false);
  const [textDialogOpen, setTextDialogOpen] = useState(false);
  const [htmlContent, setHtmlContent] = useState('');
  const [textContent, setTextContent] = useState('');

  const fetchPage = async () => {
    try {
      const res = await pageApi.get(projectId, pageId);
      setPage(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load page');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPage();
  }, [projectId, pageId]);

  const handleViewHtml = async () => {
    try {
      const res = await pageApi.getHtml(projectId, pageId);
      setHtmlContent(res.data.html);
      setHtmlDialogOpen(true);
    } catch (err) {
      setError('Failed to load HTML');
    }
  };

  const handleViewText = async () => {
    try {
      const res = await pageApi.getText(projectId, pageId);
      setTextContent(res.data.text);
      setTextDialogOpen(true);
    } catch (err) {
      setError('Failed to load text');
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'queued':
        return 'Queued';
      case 'crawling':
        return 'Crawling';
      case 'parsed':
        return 'Parsed';
      case 'analyzed':
        return 'Analyzed';
      case 'failed':
        return 'Failed';
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

  const totalWords = page?.words_count || 0;
  const foreignWords = page?.foreign_words_count || 0;
  const foreignPercentage = totalWords > 0 ? ((foreignWords / totalWords) * 100).toFixed(1) : 0;

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(`/project/${projectId}`)}>
          Back to Project
        </Button>
      </Box>

      <Typography variant="h4" gutterBottom>
        Page Analysis
      </Typography>

      <Typography variant="body1" color="text.secondary" gutterBottom>
        {page?.url}
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Chip label={getStatusLabel(page?.status)} color="primary" />
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Box sx={{ width: '100%' }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Statistics
            </Typography>
            <Box display="flex" gap={4}>
              <Typography variant="body1">Total Words: {totalWords}</Typography>
              <Typography variant="body1">Foreign Words: {foreignWords}</Typography>
              <Typography variant="body1">Foreign %: {foreignPercentage}%</Typography>
            </Box>
          </Paper>
        </Box>
      </Grid>

      <Box display="flex" gap={2} mb={3}>
        <Button
          variant="outlined"
          startIcon={<Code />}
          onClick={handleViewHtml}
        >
          View HTML
        </Button>
        <Button
          variant="outlined"
          startIcon={<Visibility />}
          onClick={handleViewText}
        >
          View Text
        </Button>
      </Box>

      <Typography variant="h5" gutterBottom>
        Detected Foreign Words
      </Typography>

      {page?.foreign_words && page.foreign_words.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Word</TableCell>
                <TableCell align="right">Count</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {page.foreign_words
                .sort((a, b) => b.count - a.count)
                .map((fw, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{fw.word}</TableCell>
                    <TableCell align="right">{fw.count}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary">No foreign words detected.</Typography>
      )}

      {/* HTML Dialog */}
      <Dialog open={htmlDialogOpen} onClose={() => setHtmlDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>HTML Content</DialogTitle>
        <DialogContent>
          <Paper variant="outlined" sx={{ p: 2, maxHeight: 500, overflow: 'auto', bgcolor: 'grey.100' }}>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
              {htmlContent}
            </pre>
          </Paper>
        </DialogContent>
      </Dialog>

      {/* Text Dialog */}
      <Dialog open={textDialogOpen} onClose={() => setTextDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Extracted Text</DialogTitle>
        <DialogContent>
          <Paper variant="outlined" sx={{ p: 2, maxHeight: 500, overflow: 'auto' }}>
            <pre style={{ whiteSpace: 'pre-wrap' }}>
              {textContent}
            </pre>
          </Paper>
        </DialogContent>
      </Dialog>
    </Container>
  );
}

export default PageDetailPage;