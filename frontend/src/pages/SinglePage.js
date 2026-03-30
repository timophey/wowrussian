import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  ArrowBack,
  Search,
  Clear,
  Visibility,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useSingleAnalysis } from '../hooks/useSingleAnalysis';
import AnalysisResults from '../components/AnalysisResults';

function SinglePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const {
    url,
    setUrl,
    loading,
    error,
    results,
    showResults,
    handleSubmit,
    handleClear,
  } = useSingleAnalysis();

  const downloadReport = () => {
    if (!results) return;
    
    const reportFormat = 'json';
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `fz168-report-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/')}
          variant="outlined"
        >
          {t('single.back')}
        </Button>
        <Typography variant="h4">
          {t('single.title')}
        </Typography>
      </Box>
      
      {/* URL Input Form */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          {t('single.urlLabel')}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {t('single.subtitle')}
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label={t('single.urlLabel')}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={t('single.urlPlaceholder')}
            disabled={loading}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
              endAdornment: url && (
                <InputAdornment position="end">
                  <IconButton onClick={() => setUrl('')} edge="end" size="small">
                    <Clear />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          
          <Box display="flex" gap={2}>
            <Button
              type="submit"
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} /> : <Search />}
              disabled={loading}
            >
              {loading ? t('single.analyzing') : t('single.analyzeButton')}
            </Button>
            <Button
              variant="outlined"
              startIcon={<Clear />}
              onClick={handleClear}
              disabled={loading}
            >
              {t('single.clear')}
            </Button>
            {results && (
              <Button
                variant="outlined"
                startIcon={<Visibility />}
                onClick={downloadReport}
                sx={{ ml: 'auto' }}
              >
                {t('single.downloadJson')}
              </Button>
            )}
          </Box>
        </form>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
      
      {/* Results Section */}
      {showResults && results && (
        <AnalysisResults results={results} />
      )}
    </Container>
  );
}

export default SinglePage;
