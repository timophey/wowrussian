import React, { useState, useEffect, useCallback } from 'react';
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
  Tabs,
  Tab,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  Upload as UploadIcon,
  Language as LanguageIcon,
  TextSnippet as TextIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import AnalysisResults from '../components/AnalysisResults';
import { authApi, projectApi, guestApi, singleApi } from '../services/api';
import useDocumentTitle from '../hooks/useDocumentTitle';
import TextFieldRounded from '../components/TextFieldRounded';

// Tab order mapping
const TAB_MAP = {
  text: { label: 'home.tabText', icon: <TextIcon /> },
  url: { label: 'home.tabUrl', icon: <SearchIcon /> },
  site: { label: 'home.tabSite', icon: <LanguageIcon /> },
  file: { label: 'home.tabFile', icon: <UploadIcon /> },
};

function HomePage() {
  const { t } = useTranslation();
  useDocumentTitle(t('home.title'), false);
  const { user, isAuthenticated } = useAuth();
  const isAdmin = user?.role === 'admin';
  const navigate = useNavigate();

  // State
  const [tabOrder, setTabOrder] = useState(['site', 'text', 'url', 'file']);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [guestSessionToken, setGuestSessionToken] = useState(null);

  // Tab-specific state
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [siteUrl, setSiteUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  // Single analysis results
  const [results, setResults] = useState(null);
  const [showResults, setShowResults] = useState(false);

  // Load tab order from backend
  useEffect(() => {
    const fetchTabOrder = async () => {
      try {
        const response = await singleApi.getConfig();
        if (response.data && response.data.tab_order) {
          setTabOrder(response.data.tab_order);
        }
      } catch (err) {
        console.error('Failed to load tab order:', err);
      }
    };
    fetchTabOrder();
  }, []);

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

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    setError('');
    setResults(null);
    setShowResults(false);
  };

  const validateUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Check file size (2MB)
      if (file.size > 2 * 1024 * 1024) {
        setError(t('home.fileTooLarge'));
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setError('');
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setError('');
  };

  const handleSubmit = useCallback(async (e) => {
    if (e) e.preventDefault();
    setError('');
    setResults(null);
    setShowResults(false);

    const currentTab = tabOrder[activeTab];

    // Validation
    if (currentTab === 'text') {
      if (!text.trim()) {
        setError(t('home.pleaseEnterText'));
        return;
      }
    } else if (currentTab === 'url') {
      if (!url.trim()) {
        setError(t('home.pleaseEnterUrl'));
        return;
      }
      if (!validateUrl(url)) {
        setError(t('home.validUrlRequired'));
        return;
      }
    } else if (currentTab === 'site') {
      if (!siteUrl.trim()) {
        setError(t('home.pleaseEnterUrl'));
        return;
      }
      if (!validateUrl(siteUrl)) {
        setError(t('home.validUrlRequired'));
        return;
      }
    } else if (currentTab === 'file') {
      if (!selectedFile) {
        setError(t('home.pleaseSelectFile'));
        return;
      }
    }

    setLoading(true);
    try {
      let response;

      if (currentTab === 'text') {
        response = await singleApi.checkText(text);
        if (response.data.success) {
          setResults(response.data.data);
          setShowResults(true);
        } else {
          setError(response.data.detail || t('home.failedToAnalyze'));
        }
      } else if (currentTab === 'url') {
        response = await singleApi.check(url);
        if (response.data.success) {
          setResults(response.data.data);
          setShowResults(true);
        } else {
          setError(response.data.detail || t('home.failedToAnalyze'));
        }
      } else if (currentTab === 'site') {
        // Site analysis creates a project
        const token = isAuthenticated ? null : guestSessionToken;
        response = await projectApi.create(siteUrl, token);
        const projectId = response.data.id;
        navigate(`/project/${projectId}`);
        return;
      } else if (currentTab === 'file') {
        response = await singleApi.checkFile(selectedFile);
        if (response.data.success) {
          setResults(response.data.data);
          setShowResults(true);
        } else {
          setError(response.data.detail || t('home.failedToAnalyze'));
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('home.failedToAnalyze'));
    } finally {
      setLoading(false);
    }
  }, [activeTab, tabOrder, text, url, siteUrl, selectedFile, isAuthenticated, guestSessionToken, navigate, t]);

  const handleClear = () => {
    setText('');
    setUrl('');
    setSiteUrl('');
    setSelectedFile(null);
    setError('');
    setResults(null);
    setShowResults(false);
  };

  const downloadReport = () => {
    if (!results) return;

    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const downloadUrl = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `fz168-report-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(downloadUrl);
  };

  return (
    <Container data-block="home-container" maxWidth="lg">
      <Box data-block="home-content" sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          {t('home.title')}
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph align="center" sx={{ mb: 4 }}>
          {t('home.subtitle')}
        </Typography>

        <Paper data-block="analysis-form" elevation={3} sx={{ p: { xs: 2, sm: 4 }, width: '100%' }}>
          {/* Tabs */}
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ mb: 3 }}
          >
            {tabOrder.map((tabKey, index) => (
              <Tab
                key={tabKey}
                icon={TAB_MAP[tabKey]?.icon}
                iconPosition="start"
                label={t(TAB_MAP[tabKey]?.label)}
                data-block={`tab-${tabKey}`}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: '#fff',
                  }
                }}
              />
            ))}
          </Tabs>

          <form onSubmit={handleSubmit}>
            <Box sx={{display: 'flex', flexDirection: 'column', gap: '36px', backgroundColor:'#F8F8FC', padding: '36px', borderRadius: '36px'}}>

              {/* Text Tab */}
              {tabOrder[activeTab] === 'text' && (
                <TextFieldRounded
                  fullWidth
                  multiline
                  rows={8}
                  // label={t('home.textLabel')}
                  variant="outlined"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={t('home.textPlaceholder')}
                  disabled={loading}
                  sx={{ mb: 2 }}
                />
              )}

              {/* URL Tab */}
              {tabOrder[activeTab] === 'url' && (
                <TextFieldRounded
                  fullWidth
                  // label={t('home.urlLabel')}
                  variant="outlined"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder={t('home.urlPlaceholder')}
                  disabled={loading}
                  sx={{ mb: 2 }}
                  helperText={t('home.urlHelper')}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start" placement="home">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                    endAdornment: url && (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setUrl('')} edge="end" size="small">
                          <ClearIcon />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              )}

              {/* Site Tab */}
              {tabOrder[activeTab] === 'site' && (
                <TextFieldRounded
                  fullWidth
                  // label={t('home.siteUrlLabel')}
                  variant="outlined"
                  value={siteUrl}
                  onChange={(e) => setSiteUrl(e.target.value)}
                  placeholder={t('home.siteUrlPlaceholder')}
                  disabled={loading}
                  sx={{ mb: 2 }}
                  helperText={t('home.siteUrlHelper')}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LanguageIcon />
                      </InputAdornment>
                    ),
                    endAdornment: siteUrl && (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setSiteUrl('')} edge="end" size="small">
                          <ClearIcon />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              )}

              {/* File Tab */}
              {tabOrder[activeTab] === 'file' && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Button
                      variant="outlined"
                      component="label"
                      startIcon={<UploadIcon />}
                      disabled={loading}
                    >
                      {t('home.fileSelectButton')}
                      <input
                        type="file"
                        hidden
                        accept=".txt,.html,.htm,.md"
                        onChange={handleFileChange}
                      />
                    </Button>
                    {selectedFile && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {t('home.fileSelected', { name: selectedFile.name })}
                        </Typography>
                        <IconButton size="small" onClick={handleClearFile}>
                          <ClearIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    {t('home.fileHelper')}
                  </Typography>
                </Box>
              )}

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {/* Start button */}
                <Button
                  data-block="analyze-button"
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : null}
                  sx={{ flex: { xs: '0 1 auto', sm: 1 }, padding: '12.5px 28px' }}
                >
                  {loading ? (tabOrder[activeTab] === 'site' ? t('home.creating') : t('home.analyzing')) : t('home.analyzeButton')}
                </Button>
                {/* Clear button */}
                {false && <Button
                  variant="outlined"
                  size="large"
                  onClick={handleClear}
                  disabled={loading}
                  startIcon={<ClearIcon />}
                >
                  {t('single.clear')}
                </Button>}
                {results && (
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={downloadReport}
                    startIcon={<SearchIcon />}
                  >
                    {t('single.downloadJson')}
                  </Button>
                )}
              </Box>

            </Box>
          </form>
        </Paper>

        <Box data-block="home-description" sx={{ mt: 4, mb: 4, width: '100%' }}>
          <Typography variant="body2" color="text.secondary" align="center">
            {t('home.description')}
          </Typography>
        </Box>

        {/* Results Section */}
        {showResults && results && (
          <AnalysisResults results={results} isAdmin={isAdmin} />
        )}
      </Box>
    </Container>
  );
}

export default HomePage;
