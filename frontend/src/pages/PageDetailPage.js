import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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

  // Get language display name
  const getLanguageName = (code) => {
    if (!code) return t('page.unknown');
    return t(`language.${code.toLowerCase()}`, { defaultValue: code.toUpperCase() });
  };

  // Get classification based on language
  const getClassification = (languageGuess) => {
    if (!languageGuess) return t('classification.foreign');
    const lang = languageGuess.toLowerCase();
    if (lang === 'en') return t('classification.anglicism');
    if (lang === 'fr') return t('classification.gallicism');
    if (lang === 'de') return t('classification.germanism');
    if (lang === 'it') return t('classification.italianism');
    if (lang === 'es') return t('classification.hispanism');
    if (lang === 'ru') return t('classification.russian');
    return t('classification.foreign');
  };

  // Get classification color
  const getClassificationColor = (languageGuess) => {
    const classification = getClassification(languageGuess);
    switch (classification) {
      case t('classification.anglicism'):
        return 'error';
      case t('classification.gallicism'):
        return 'secondary';
      case t('classification.germanism'):
        return 'warning';
      case t('classification.italianism'):
        return 'info';
      case t('classification.hispanism'):
        return 'success';
      default:
        return 'default';
    }
  };

  const fetchPage = async () => {
    try {
      const res = await pageApi.get(projectId, pageId);
      setPage(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('errors.failedToLoad'));
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
      setError(t('errors.failedToLoadHtml'));
    }
  };

  const handleViewText = async () => {
    try {
      const res = await pageApi.getText(projectId, pageId);
      setTextContent(res.data.text);
      setTextDialogOpen(true);
    } catch (err) {
      setError(t('errors.failedToLoadText'));
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'queued':
        return t('status.queued');
      case 'crawling':
        return t('status.crawling');
      case 'parsed':
        return t('status.parsed');
      case 'analyzed':
        return t('status.analyzed');
      case 'failed':
        return t('status.failed');
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
    <Container maxWidth="lg" sx={{ mt: 8 }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(`/project/${projectId}`)}>
          {t('page.backToProject')}
        </Button>
      </Box>

      <Typography variant="h4" gutterBottom>
        {t('page.pageAnalysis')}
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
              {t('page.statistics')}
            </Typography>
            <Box display="flex" gap={4}>
              <Typography variant="body1">{t('page.totalWords')}: {totalWords}</Typography>
              <Typography variant="body1">{t('page.foreignWords')}: {foreignWords}</Typography>
              <Typography variant="body1">{t('page.foreignPercent')}: {foreignPercentage}%</Typography>
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
          {t('page.viewHtml')}
        </Button>
        <Button
          variant="outlined"
          startIcon={<Visibility />}
          onClick={handleViewText}
        >
          {t('page.viewText')}
        </Button>
      </Box>

      <Typography variant="h5" gutterBottom>
        {t('page.detectedForeignWords')}
      </Typography>

      {page?.foreign_words && page.foreign_words.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('page.word')}</TableCell>
                <TableCell>{t('page.language')}</TableCell>
                <TableCell>{t('page.type')}</TableCell>
                <TableCell align="right">{t('page.count')}</TableCell>
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
        <Typography color="text.secondary">{t('page.noForeignWords')}</Typography>
      )}

    <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
      {t('page.russianWordsFound')}
    </Typography>
    {page?.russian_words && page.russian_words.length > 0 ? (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{t('page.word')}</TableCell>
              <TableCell>{t('page.dictionarySource')}</TableCell>
              <TableCell align="right">{t('page.count')}</TableCell>
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
                      label={rw.source === 'dictionary' ? t('page.mainDictionary') :
                             rw.source === 'fallback' ? t('page.fallbackDictionary') : t('page.unknown')}
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
      <Typography color="text.secondary">{t('page.noRussianWords')}</Typography>
    )}

    {/* HTML Dialog */}
      <Dialog open={htmlDialogOpen} onClose={() => setHtmlDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('dialogs.htmlContent')}</DialogTitle>
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
        <DialogTitle>{t('page.extractedText')}</DialogTitle>
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