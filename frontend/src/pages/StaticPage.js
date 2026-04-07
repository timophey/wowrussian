import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Container, Typography, Paper, CircularProgress, Alert, Box } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

function StaticPage() {
  const { t, i18n } = useTranslation();
  const { url: paramUrl } = useParams();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(null);
  const [error, setError] = useState('');

  // Extract URL from either route param or pathname
  const getPageUrl = () => {
    if (paramUrl) return paramUrl;
    // Extract from pathname: /privacy-policy -> privacy-policy
    const path = location.pathname.replace(/^\//, '');
    return path;
  };

  const url = getPageUrl();

  useEffect(() => {
    const lang = i18n.language === 'ru' ? 'ru' : 'en';
    axios.get(`${API_BASE_URL}/static-pages/${url}?lang=${lang}`)
      .then(response => {
        setPage(response.data);
        setLoading(false);
      })
      .catch(err => {
        if (err.response?.status === 404) {
          // Try fallback to Russian if current language is not Russian
          if (lang !== 'ru') {
            axios.get(`${API_BASE_URL}/static-pages/${url}?lang=ru`)
              .then(response => {
                setPage(response.data);
                setLoading(false);
              })
              .catch(() => {
                setError(t('errors.notFound'));
                setLoading(false);
              });
          } else {
            setError(t('errors.notFound'));
            setLoading(false);
          }
        } else {
          setError(t('errors.failedToLoad'));
          setLoading(false);
        }
      });
  }, [url, i18n.language, t]);

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 8, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container data-block="static-page-container" maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          {page.title}
        </Typography>
        <Box sx={{ mt: 4 }}>
          <ReactMarkdown>{page.content_md || ''}</ReactMarkdown>
        </Box>
      </Paper>
    </Container>
  );
}

export default StaticPage;
