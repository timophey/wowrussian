import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { singleApi } from '../services/api';

export function useSingleAnalysis() {
  const { t } = useTranslation();
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  const [showResults, setShowResults] = useState(false);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    
    if (!url.trim()) {
      setError(t('home.pleaseEnterUrl'));
      return;
    }
    
    // Ensure URL has protocol
    let fullUrl = url.trim();
    if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
      fullUrl = 'https://' + fullUrl;
    }
    
    setError('');
    setLoading(true);
    setShowResults(false);
    
    try {
      const response = await singleApi.check(fullUrl);
      if (response.data.success) {
        setResults(response.data.data);
        setShowResults(true);
      } else {
        setError(response.data.detail || t('errors.failedToLoad'));
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('errors.failedToLoad'));
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setUrl('');
    setResults(null);
    setShowResults(false);
    setError('');
  };

  return {
    url,
    setUrl,
    loading,
    error,
    results,
    showResults,
    handleSubmit,
    handleClear,
  };
}
