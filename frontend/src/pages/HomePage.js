import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Container,
  TextField,
  Button,
  Typography,
  Box,
  Paper,
  Alert,
  CircularProgress,
} from '@mui/material';
import { projectApi } from '../services/api';

function HomePage() {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const validateUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const extractDomain = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch {
      return url;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!url.trim()) {
      setError(t('home.pleaseEnterUrl'));
      return;
    }

    if (!validateUrl(url)) {
      setError(t('home.validUrlRequired'));
      return;
    }

    setLoading(true);
    try {
      const response = await projectApi.create(url);
      const projectId = response.data.id;
      navigate(`/project/${projectId}`);
    } catch (err) {
      setError(err.response?.data?.detail || t('home.failedToCreate'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h3" component="h1" gutterBottom>
          {t('home.title')}
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph align="center" sx={{ mb: 4 }}>
          {t('home.subtitle')}
        </Typography>

        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label={t('home.urlLabel')}
              variant="outlined"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t('home.urlPlaceholder')}
              disabled={loading}
              sx={{ mb: 2 }}
              helperText={t('home.urlHelper')}
            />

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              {loading ? t('home.creating') : t('home.analyzeButton')}
            </Button>
          </form>
        </Paper>

        <Box sx={{ mt: 4, width: '100%' }}>
          <Typography variant="body2" color="text.secondary" align="center">
            {t('home.description')}
          </Typography>
        </Box>

        <Box sx={{ mt: 3 }}>
          <Button
            variant="outlined"
            size="large"
            fullWidth
            onClick={() => navigate('/projects')}
          >
            {t('home.viewAllProjects')}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}

export default HomePage;