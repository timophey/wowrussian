import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Container, Box, IconButton, Typography, Button, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Alert, CircularProgress, Divider } from '@mui/material';
import { Visibility, Person, Logout, Language as LanguageIcon } from '@mui/icons-material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import HomePage from './pages/HomePage';
import ProjectPage from './pages/ProjectPage';
import ProjectsListPage from './pages/ProjectsListPage';
import PageDetailPage from './pages/PageDetailPage';
import SinglePage from './pages/SinglePage';
import AdminPage from './pages/AdminPage';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { authApi } from './services/api';
import './i18n';

function Header() {
  const { t, i18n } = useTranslation();
  const { user, logout, isAuthenticated, login } = useAuth();
  const navigate = useNavigate();

  const [authDialogOpen, setAuthDialogOpen] = React.useState(false);
  const [authMode, setAuthMode] = React.useState('login');
  const [authLoading, setAuthLoading] = React.useState(false);
  const [authError, setAuthError] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');

  const handleLogout = () => {
    logout();
  };

  const handleOpenAuthDialog = (mode) => {
    setAuthMode(mode);
    setAuthDialogOpen(true);
    setAuthError('');
    setEmail('');
    setPassword('');
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
        result = await authApi.register(email, password);
        // Auto-login after registration
        if (result.success) {
          result = await login(email, password);
        }
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

  return (
    <Box
      data-block="header"
      sx={{
        position: 'fixed',
        top: 16,
        right: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        zIndex: 1000,
      }}
    >
      {/* Language Switcher */}
      <Tooltip title={i18n.language === 'ru' ? 'Switch to English' : 'Переключить на русский'}>
        <IconButton
          onClick={() => {
            const newLang = i18n.language === 'ru' ? 'en' : 'ru';
            i18n.changeLanguage(newLang);
          }}
          size="small"
          sx={{
            bgcolor: 'background.paper',
            borderRadius: 1,
            '&:hover': {
              bgcolor: 'background.paper',
            },
          }}
        >
          <LanguageIcon fontSize="small" />
          <Typography variant="body2" component="span" sx={{ ml: 0.5, fontSize: '0.875rem' }}>
            {i18n.language === 'ru' ? 'EN' : 'RU'}
          </Typography>
        </IconButton>
      </Tooltip>

      {/* Auth Controls */}
      {isAuthenticated && user ? (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
            {t('home.loggedInAs')}: {user.email}
          </Typography>
          <Tooltip title={t('home.logout')}>
            <IconButton size="small" onClick={handleLogout}>
              <Logout />
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            size="small"
            startIcon={<Visibility />}
            onClick={() => navigate('/projects')}
            sx={{ display: { xs: 'none', sm: 'flex' } }}
          >
            {t('home.viewAllProjects')}
          </Button>
        </>
      ) : (
        <Button
          variant="contained"
          size="small"
          startIcon={<Person />}
          onClick={() => handleOpenAuthDialog('login')}
        >
          {t('home.login')}
        </Button>
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
          <Button size="small" onClick={() => handleOpenAuthDialog(authMode === 'login' ? 'register' : 'login')}>
            {authMode === 'login' ? t('home.noAccount') : t('home.haveAccount')}
          </Button>
        </Box>
      </Dialog>
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <Header />
      <Container data-block="main-container" maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectsListPage />} />
          <Route path="/project/:id" element={<ProjectPage />} />
          <Route path="/project/:projectId/page/:pageId" element={<PageDetailPage />} />
          <Route path="/single" element={<SinglePage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Container>
    </AuthProvider>
  );
}

export default App;
