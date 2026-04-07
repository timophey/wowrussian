import React from 'react';
import { Routes, Route, Navigate, Link as RouterLink } from 'react-router-dom';
import { Container, Box, IconButton, Typography, Button, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Alert, CircularProgress, Divider, Link } from '@mui/material';
import { Visibility, Person, Logout, Language as LanguageIcon, Settings as SettingsIcon } from '@mui/icons-material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import HomePage from './pages/HomePage';
import NewProjectPage from './pages/NewProjectPage';
import ProjectPage from './pages/ProjectPage';
import ProjectsListPage from './pages/ProjectsListPage';
import PageDetailPage from './pages/PageDetailPage';
import SinglePage from './pages/SinglePage';
import AdminPage from './pages/AdminPage';
import UserProfilePage from './pages/UserProfilePage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import LegalInfoPage from './pages/LegalInfoPage';
import StaticPage from './pages/StaticPage';
import Footer from './components/Footer';
import CookieConsentBanner from './components/CookieConsentBanner';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { authApi } from './services/api';
import './i18n';

function Header() {
  const { t, i18n } = useTranslation();
  const { user, logout, isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();

  const [authDialogOpen, setAuthDialogOpen] = React.useState(false);
  const [authMode, setAuthMode] = React.useState('login');
  const [authLoading, setAuthLoading] = React.useState(false);
  const [authError, setAuthError] = React.useState('');
  const [authSuccess, setAuthSuccess] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [consentGiven, setConsentGiven] = React.useState(false);

  const handleLogout = () => {
    logout();
  };

  const handleOpenAuthDialog = (mode) => {
    setAuthMode(mode);
    setAuthDialogOpen(true);
    setAuthError('');
    setAuthSuccess('');
    setEmail('');
    setPassword('');
    setConsentGiven(false);
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthSuccess('');
    
    // Check consent for registration
    if (authMode === 'register' && !consentGiven) {
      setAuthError(t('home.consentRequired'));
      return;
    }
    
    setAuthLoading(true);

    try {
      let result;
      if (authMode === 'login') {
        result = await login(email, password);
      } else {
        result = await register(email, password);
      }

      if (result.success) {
        if (authMode === 'register') {
          // Show success message and switch to login
          setAuthSuccess(t('home.registrationSuccess'));
          setAuthMode('login');
          setEmail('');
          setPassword('');
        } else {
          setAuthDialogOpen(false);
          setEmail('');
          setPassword('');
        }
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
        top: 0,
        left: 0,
        right: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        bgcolor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider',
        zIndex: 1100,
        boxShadow: 1,
      }}
    >
      {/* Logo */}
      <Box
        component={RouterLink}
        to="/"
        sx={{
          display: 'flex',
          alignItems: 'center',
          textDecoration: 'none',
          '&:hover': {
            opacity: 0.8,
          },
        }}
      >
        <img
          src={`${process.env.PUBLIC_URL}/logos/${process.env.REACT_APP_LOGO_FILE || 'logo-icon-text.svg'}`}
          alt="WowRussian"
          style={{ height: '36px', width: 'auto' }}
        />
      </Box>

      {/* Right side controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
          <Tooltip title={t('profile.title')}>
            <IconButton size="small" onClick={() => navigate('/profile')} color="primary">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
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
            {authMode === 'register' && (
              <Box sx={{ display: 'flex', alignItems: 'flex-start', mt: 1, mb: 1 }}>
                <input
                  type="checkbox"
                  id="consent-checkbox"
                  checked={consentGiven}
                  onChange={(e) => setConsentGiven(e.target.checked)}
                  style={{ marginTop: 8, marginRight: 8 }}
                />
                <label htmlFor="consent-checkbox" style={{ fontSize: '0.875rem', lineHeight: 1.5 }}>
                  {t('home.consentText')}{' '}
                  <Link href="/privacy-policy" target="_blank" rel="noopener noreferrer">
                    {t('home.privacyPolicyLink')}
                  </Link>
                </label>
              </Box>
            )}
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
            {authSuccess && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {authSuccess}
              </Alert>
            )}
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
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <Header />
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}
      >
        <Container data-block="main-container" maxWidth="lg" sx={{ mt: 8, flex: 1, pb: 8 }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/newproject" element={<NewProjectPage />} />
            <Route path="/projects" element={<ProjectsListPage />} />
            <Route path="/profile" element={<UserProfilePage />} />
            <Route path="/project/:id" element={<ProjectPage />} />
            <Route path="/project/:projectId/page/:pageId" element={<PageDetailPage />} />
            <Route path="/single" element={<SinglePage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/privacy-policy" element={<StaticPage />} />
            <Route path="/legal-info" element={<StaticPage />} />
            <Route path="/p/:url" element={<StaticPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
        <Footer />
        <CookieConsentBanner />
      </Box>
    </AuthProvider>
  );
}

export default App;
