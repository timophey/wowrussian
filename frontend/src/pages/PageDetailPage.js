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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { ArrowBack, Visibility, Code, ExpandMore, Assessment, MenuBook, CheckCircle, Warning } from '@mui/icons-material';
import { pageApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

function PageDetailPage() {
  const { t } = useTranslation();
  const { projectId, pageId } = useParams();
  const { isAuthenticated } = useAuth();
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
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const res = await pageApi.get(projectId, pageId, guestToken);
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
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const res = await pageApi.getHtml(projectId, pageId, guestToken);
      setHtmlContent(res.data.html);
      setHtmlDialogOpen(true);
    } catch (err) {
      setError(t('errors.failedToLoadHtml'));
    }
  };

  const handleViewText = async () => {
    try {
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      const res = await pageApi.getText(projectId, pageId, guestToken);
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

    {/* 168-FZ Metadata Section */}
    {(page.fz168_statistics || page.fz168_summary || page.fz168_checks || page.fz168_dictionaries) ? (
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          {t('fz168.title')}
        </Typography>

        {/* Summary Panel */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center" gap={1}>
              <Assessment />
              <Typography>{t('fz168.summary')}</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {page.fz168_summary && Object.keys(page.fz168_summary).length > 0 ? (
              <Grid container spacing={2}>
                {Object.entries(page.fz168_summary).map(([key, value]) => (
                  <Grid item xs={6} sm={3} key={key}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" gutterBottom>
                          {t(`fz168.${key}`, { defaultValue: key.replace(/_/g, ' ') })}
                        </Typography>
                        <Typography variant="h6">{value}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography color="text.secondary">{t('fz168.noMetadata')}</Typography>
            )}
          </AccordionDetails>
        </Accordion>

        {/* Checks Panel */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center" gap={1}>
              <CheckCircle />
              <Typography>{t('fz168.checks')}</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {page.fz168_checks && Object.keys(page.fz168_checks).length > 0 ? (
              <List>
                {Object.entries(page.fz168_checks).map(([key, check]) => (
                  <React.Fragment key={key}>
                    <ListItem>
                      <ListItemText
                        primary={key}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="textSecondary">
                              {t('fz168.dictionary')}: {check.dictionary || '-'}
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              {t('fz168.explanation')}: {check.explanation || '-'}
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              {t('fz168.lawArticle')}: {check.law_article || '-'}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Typography color="text.secondary">{t('fz168.noMetadata')}</Typography>
            )}
          </AccordionDetails>
        </Accordion>

        {/* Statistics Panel */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center" gap={1}>
              <MenuBook />
              <Typography>{t('fz168.statistics')}</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {page.fz168_statistics ? (
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                {JSON.stringify(page.fz168_statistics, null, 2)}
              </pre>
            ) : (
              <Typography color="text.secondary">{t('fz168.noMetadata')}</Typography>
            )}
          </AccordionDetails>
        </Accordion>

        {/* Dictionaries Panel */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center" gap={1}>
              <Warning />
              <Typography>{t('fz168.dictionaries')}</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {page.fz168_dictionaries && page.fz168_dictionaries.length > 0 ? (
              <List>
                {page.fz168_dictionaries.map((dict, idx) => (
                  <ListItem key={idx}>
                    <ListItemText
                      primary={dict.name || dict.id}
                      secondary={`${t('fz168.dictionary')}: ${dict.type || 'unknown'}`}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography color="text.secondary">{t('fz168.noMetadata')}</Typography>
            )}
          </AccordionDetails>
        </Accordion>
      </Box>
    ) : null}

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