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

// Language code to name mapping
const LANGUAGE_NAMES = {
  'en': 'English',
  'fr': 'French',
  'de': 'German',
  'es': 'Spanish',
  'it': 'Italian',
  'pt': 'Portuguese',
  'ru': 'Russian',
  'uk': 'Ukrainian',
  'pl': 'Polish',
  'cs': 'Czech',
  'nl': 'Dutch',
  'sv': 'Swedish',
  'no': 'Norwegian',
  'da': 'Danish',
  'fi': 'Finnish',
  'el': 'Greek',
  'tr': 'Turkish',
  'ar': 'Arabic',
  'he': 'Hebrew',
  'ja': 'Japanese',
  'ko': 'Korean',
  'zh': 'Chinese',
  'hi': 'Hindi',
  'th': 'Thai',
  'vi': 'Vietnamese',
};

// Get language display name
const getLanguageName = (code) => {
  if (!code) return 'Unknown';
  return LANGUAGE_NAMES[code.toLowerCase()] || code.toUpperCase();
};

// Get classification based on language
const getClassification = (languageGuess) => {
  if (!languageGuess) return 'Foreign';
  const lang = languageGuess.toLowerCase();
  if (lang === 'en') return 'Anglicism';
  if (lang === 'fr') return 'Gallicism';
  if (lang === 'de') return 'Germanism';
  if (lang === 'it') return 'Italianism';
  if (lang === 'es') return 'Hispanism';
  if (lang === 'ru') return 'Russian';
  return 'Foreign';
};

// Get classification color
const getClassificationColor = (languageGuess) => {
  const classification = getClassification(languageGuess);
  switch (classification) {
    case 'Anglicism':
      return 'error'; // red
    case 'Gallicism':
      return 'secondary'; // pink/purple
    case 'Germanism':
      return 'warning'; // orange
    case 'Italianism':
      return 'info'; // light blue
    case 'Hispanism':
      return 'success'; // green
    default:
      return 'default';
  }
};

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
                <TableCell>Language</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Count</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {page.foreign_words
                .sort((a, b) => b.count - a.count)
                .map((fw, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{fw.word}</TableCell>
                    <TableCell>{getLanguageName(fw.language_guess)}</TableCell>
                    <TableCell>
                      <Chip
                        label={getClassification(fw.language_guess)}
                        color={getClassificationColor(fw.language_guess)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">{fw.count}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary">No foreign words detected.</Typography>
      )}

    <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
      Russian Words Found
    </Typography>
    {page?.russian_words && page.russian_words.length > 0 ? (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Word</TableCell>
              <TableCell>Dictionary Source</TableCell>
              <TableCell align="right">Count</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {page.russian_words
              .sort((a, b) => b.count - a.count)
              .map((rw, idx) => (
                <TableRow key={idx}>
                  <TableCell>{rw.word}</TableCell>
                  <TableCell>
                    <Chip
                      label={rw.source === 'dictionary' ? 'Main Dictionary' :
                             rw.source === 'fallback' ? 'Fallback Dictionary' : 'Unknown'}
                      color={rw.source === 'dictionary' ? 'success' :
                             rw.source === 'fallback' ? 'warning' : 'default'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">{rw.count}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>
    ) : (
      <Typography color="text.secondary">No Russian words data available.</Typography>
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