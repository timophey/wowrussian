import React, { useState, useEffect } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Divider,
} from '@mui/material';
import { Visibility, Person, Logout } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { authApi, projectApi, guestApi } from '../services/api';
import useDocumentTitle from '../hooks/useDocumentTitle';

function NewProjectPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('projects.newAnalysis'));
  const { user, login, logout, isAuthenticated } = useAuth();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [guestSessionToken, setGuestSessionToken] = useState(null);
  const navigate = useNavigate();

  // Initialize guest session for unauthenticated users
  useEffect(() => {
    if (!isAuthenticated) {
      const existingToken = localStorage.getItem('guest_session_token');
      if (existingToken) {
        setGuestSessionToken(existingToken);
      } else {
        createGuestSession();
      }
    }
  }, [isAuthenticated]);

  const createGuestSession = async () => {
    try {
      const response = await guestApi.createSession();
      const token = response.data.session_token;
      localStorage.setItem('guest_session_token', token);
      setGuestSessionToken(token);
    } catch (err) {
      console.error('Failed to create guest session:', err);
    }
  };

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
      // Use guest session token if not authenticated
      const token = isAuthenticated ? null : guestSessionToken;
      const response = await projectApi.create(url, token);
      const projectId = response.data.id;
      navigate(`/project/${projectId}`);
    } catch (err) {
      setError(err.response?.data?.detail || t('home.failedToCreate'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container data-block="new-project-container" maxWidth="md">
      <Box data-block="new-project-content" sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h3" component="h1" gutterBottom>
          {t('home.title')}
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph align="center" sx={{ mb: 4 }}>
          {t('home.subtitle')}
        </Typography>

        <Paper data-block="url-form" elevation={3} sx={{ p: 4, width: '100%' }}>
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
              data-block="analyze-button"
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

        <Box data-block="new-project-description" sx={{ mt: 4, width: '100%' }}>
          <Typography variant="body2" color="text.secondary" align="center">
            {t('home.description')}
          </Typography>
        </Box>
      </Box>
    </Container>
  );
}

export default NewProjectPage;
