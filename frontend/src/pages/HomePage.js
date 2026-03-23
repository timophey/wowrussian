import React, { useState, useContext } from 'react';
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
import { authApi } from '../services/api';

function HomePage() {
  const { t } = useTranslation();
  const { user, login, logout, isAuthenticated } = useAuth();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);

    try {
      let result;
      if (authMode === 'login') {
        result = await login(email, password);
      } else {
        result = await register(email, password);
      }

      if (result.success) {
        setAuthDialogOpen(false);
        setEmail('');
        setPassword('');
      } else {
        setAuthError(result.error);
      }
    } catch (err) {
      setAuthError(t('errors.failedToLoad'));
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  const openAuthDialog = (mode) => {
    setAuthMode(mode);
    setAuthDialogOpen(true);
    setAuthError('');
    setEmail('');
    setPassword('');
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

        {/* User info bar */}
        {isAuthenticated && user && (
          <Box sx={{ width: '100%', mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {t('home.loggedInAs')}: {user.email}
            </Typography>
            <Button size="small" startIcon={<Logout />} onClick={handleLogout}>
              {t('home.logout')}
            </Button>
          </Box>
        )}

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

        {/* Show View All Projects only if authenticated */}
        {isAuthenticated ? (
          <Box sx={{ mt: 3, width: '100%' }}>
            <Button
              variant="outlined"
              size="large"
              fullWidth
              onClick={() => navigate('/projects')}
              startIcon={<Visibility />}
            >
              {t('home.viewAllProjects')}
            </Button>
          </Box>
        ) : (
          <Box sx={{ mt: 3, width: '100%' }}>
            <Button
              variant="outlined"
              size="large"
              fullWidth
              onClick={() => openAuthDialog('login')}
              startIcon={<Person />}
            >
              {t('home.loginToViewProjects')}
            </Button>
          </Box>
        )}

        {/* Auth Dialog */}
        <Dialog open={authDialogOpen} onClose={() => setAuthDialogOpen(false)} maxWidth="xs" fullWidth>
          <DialogTitle>
            {authMode === 'login' ? t('home.login') : t('home.register')}
          </DialogTitle>
          <form onSubmit={handleAuthSubmit}>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                label={t('home.email')}
                type="email"
                fullWidth
                variant="outlined"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                sx={{ mb: 2 }}
                required
              />
              <TextField
                margin="dense"
                label={t('home.password')}
                type="password"
                fullWidth
                variant="outlined"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                inputProps={{ minLength: 8 }}
              />
              {authError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {authError}
                </Alert>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setAuthDialogOpen(false)}>
                {t('dialogs.cancel')}
              </Button>
              <Button type="submit" variant="contained" disabled={authLoading}>
                {authLoading ? <CircularProgress size={20} /> : (authMode === 'login' ? t('home.login') : t('home.register'))}
              </Button>
            </DialogActions>
          </form>
          <Divider />
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Button size="small" onClick={() => openAuthDialog(authMode === 'login' ? 'register' : 'login')}>
              {authMode === 'login' ? t('home.noAccount') : t('home.haveAccount')}
            </Button>
          </Box>
        </Dialog>
      </Box>
    </Container>
  );
}

export default HomePage;