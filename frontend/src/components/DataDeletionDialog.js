import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Box,
} from '@mui/material';
import { Warning as WarningIcon } from '@mui/icons-material';
import { authApi, guestApi } from '../services/api';

function DataDeletionDialog({ open, onClose, isGuest }) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleDelete = async () => {
    setLoading(true);
    setError('');
    
    try {
      if (isGuest) {
        const guestToken = localStorage.getItem('guest_session_token');
        if (guestToken) {
          await guestApi.deleteSession(guestToken);
        }
        localStorage.removeItem('guest_session_token');
      } else {
        await authApi.deleteAccount();
        localStorage.removeItem('access_token');
      }
      
      setSuccess(true);
      
      // Redirect to home after a short delay
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || t('dataDeletion.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="error" />
          {t('dataDeletion.title')}
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" paragraph>
          {t('dataDeletion.description')}
        </Typography>
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t('dataDeletion.confirmMessage')}
        </Alert>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mt: 2 }}>
            {t('dataDeletion.success')}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading || success}>
          {t('dialogs.cancel')}
        </Button>
        <Button
          onClick={handleDelete}
          variant="contained"
          color="error"
          disabled={loading || success}
          startIcon={loading ? <CircularProgress size={20} /> : <WarningIcon />}
        >
          {loading ? t('home.creating') : t('dataDeletion.button')}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default DataDeletionDialog;
