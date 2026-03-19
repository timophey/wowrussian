import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
      setError('Please enter a URL');
      return;
    }

    if (!validateUrl(url)) {
      setError('Please enter a valid URL (including http:// or https://)');
      return;
    }

    setLoading(true);
    try {
      const response = await projectApi.create(url);
      const projectId = response.data.id;
      navigate(`/project/${projectId}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h3" component="h1" gutterBottom>
          WowRussian Analyzer
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph align="center" sx={{ mb: 4 }}>
          Analyze websites for foreign words and anglicisms
        </Typography>

        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Website URL"
              variant="outlined"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              disabled={loading}
              sx={{ mb: 2 }}
              helperText="Enter the full URL of the website you want to analyze"
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
              {loading ? 'Creating...' : 'Analyze'}
            </Button>
          </form>
        </Paper>

        <Box sx={{ mt: 4, width: '100%' }}>
          <Typography variant="body2" color="text.secondary" align="center">
            The analyzer will crawl the website, extract text content, and identify foreign words.
            <br />
            Results will be available in real-time as the analysis progresses.
          </Typography>
        </Box>
|
        <Box sx={{ mt: 3 }}>
          <Button
            variant="outlined"
            size="large"
            fullWidth
            onClick={() => navigate('/projects')}
          >
            View All Projects
          </Button>
        </Box>
      </Box>
    </Container>
  );
}

export default HomePage;