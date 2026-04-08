import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import { ArrowBack, Lock, DeleteForever } from '@mui/icons-material';
import { authApi } from '../services/api';
import DataDeletionDialog from '../components/DataDeletionDialog';
import useDocumentTitle from '../hooks/useDocumentTitle';

function UserProfilePage() {
  const { t } = useTranslation();
  useDocumentTitle(t('profile.title'));
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  
  // Account deletion state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');
    
    if (newPassword !== confirmPassword) {
      setPasswordError(t('profile.passwordsDoNotMatch'));
      return;
    }
    
    if (newPassword.length < 8) {
      setPasswordError(t('errors.weakPassword'));
      return;
    }
    
    setPasswordLoading(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setPasswordSuccess(t('profile.passwordChanged'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.toLowerCase().includes('current password')) {
        setPasswordError(t('profile.incorrectCurrentPassword'));
      } else {
        setPasswordError(detail || t('profile.failedToChangePassword'));
      }
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await authApi.deleteAccount();
      localStorage.removeItem('access_token');
      logout();
      navigate('/');
    } catch (err) {
      console.error('Failed to delete account:', err);
    }
  };

  if (!user) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Alert severity="info">{t('profile.loginRequired')}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate(-1)}
          sx={{ mr: 2 }}
        >
          {t('profile.back')}
        </Button>
        <Typography variant="h4">{t('profile.title')}</Typography>
      </Box>

      {/* User Info Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t('profile.accountInfo')}
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('home.email')}
            </Typography>
            <Typography variant="body1">
              {user.email}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('profile.role')}
            </Typography>
            <Typography variant="body1">
              {user.role === 'admin' ? t('profile.adminRole') : t('profile.userRole')}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('profile.memberSince')}
            </Typography>
            <Typography variant="body1">
              {new Date(user.created_at).toLocaleDateString()}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Password Change Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Lock sx={{ mr: 1 }} />
          <Typography variant="h6">{t('profile.changePassword')}</Typography>
        </Box>
        
        {passwordError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {passwordError}
          </Alert>
        )}
        {passwordSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {passwordSuccess}
          </Alert>
        )}
        
        <form onSubmit={handlePasswordChange}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label={t('profile.currentPassword')}
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label={t('profile.newPassword')}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              fullWidth
              inputProps={{ minLength: 8 }}
            />
            <TextField
              label={t('profile.confirmNewPassword')}
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              fullWidth
              inputProps={{ minLength: 8 }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={passwordLoading}
              sx={{ alignSelf: 'flex-start' }}
            >
              {passwordLoading ? <CircularProgress size={20} /> : t('profile.changePassword')}
            </Button>
          </Box>
        </form>
      </Paper>

      {/* Danger Zone */}
      <Paper sx={{ p: 3, border: '1px solid', borderColor: 'error.light' }}>
        <Typography variant="h6" color="error" gutterBottom>
          {t('profile.dangerZone')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('profile.deleteAccountDescription')}
        </Typography>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteForever />}
          onClick={() => setDeleteDialogOpen(true)}
        >
          {t('dataDeletion.button')}
        </Button>
      </Paper>

      {/* Data Deletion Dialog */}
      <DataDeletionDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        isGuest={false}
      />
    </Container>
  );
}

export default UserProfilePage;
