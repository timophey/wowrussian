import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
} from '@mui/material';
import { Add, Delete, ArrowBack, Visibility } from '@mui/icons-material';
import { adminApi } from '../services/api';

function AdminPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [adminKey, setAdminKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [creating, setCreating] = useState(false);

  // Check if admin key is stored
  useEffect(() => {
    const storedKey = localStorage.getItem('admin_key');
    if (storedKey) {
      setAdminKey(storedKey);
      setIsAuthenticated(true);
      fetchUsers(storedKey);
    }
  }, []);

  const fetchUsers = async (key) => {
    setLoading(true);
    setError('');
    try {
      const res = await adminApi.listUsers(key);
      setUsers(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToLoadUsers'));
      setIsAuthenticated(false);
      localStorage.removeItem('admin_key');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (e) => {
    e.preventDefault();
    if (!adminKey.trim()) {
      setError(t('admin.enterAdminKey'));
      return;
    }
    localStorage.setItem('admin_key', adminKey);
    setIsAuthenticated(true);
    fetchUsers(adminKey);
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_key');
    setAdminKey('');
    setIsAuthenticated(false);
    setUsers([]);
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUserEmail.trim() || !newUserPassword.trim()) {
      setError(t('admin.fillAllFields'));
      return;
    }
    setCreating(true);
    setError('');
    try {
      await adminApi.createUser(newUserEmail, newUserPassword, adminKey);
      setCreateDialogOpen(false);
      setNewUserEmail('');
      setNewUserPassword('');
      fetchUsers(adminKey);
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToCreateUser'));
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm(t('admin.confirmDeleteUser'))) {
      return;
    }
    try {
      await adminApi.deleteUser(userId, adminKey);
      fetchUsers(adminKey);
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToDeleteUser'));
    }
  };

  if (!isAuthenticated) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom>
            {t('admin.adminPanel')}
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {t('admin.adminDescription')}
          </Typography>
          <form onSubmit={handleLogin}>
            <TextField
              fullWidth
              label={t('admin.adminKey')}
              variant="outlined"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              type="password"
              sx={{ mb: 2 }}
              autoFocus
            />
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            <Button
              type="submit"
              variant="contained"
              fullWidth
              size="large"
            >
              {t('admin.login')}
            </Button>
          </form>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 8 }}>
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mb: 3 }}>
          <Typography variant="h4">{t('admin.adminPanel')}</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => setCreateDialogOpen(true)}
            >
              {t('admin.createUser')}
            </Button>
            <Button
              variant="text"
              startIcon={<ArrowBack />}
              onClick={() => navigate('/projects')}
            >
              {t('admin.backToProjects')}
            </Button>
            <Button
              variant="text"
              color="error"
              onClick={handleLogout}
            >
              {t('admin.logout')}
            </Button>
          </Box>
        </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('admin.userId')}</TableCell>
                <TableCell>{t('admin.email')}</TableCell>
                <TableCell>{t('admin.createdAt')}</TableCell>
                <TableCell align="right">{t('admin.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell>{user.id}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
                   <TableCell align="right">
                     <IconButton
                       size="small"
                       onClick={() => navigate(`/projects?user_id=${user.id}`)}
                       title={t('admin.viewUserProjects')}
                     >
                       <Visibility fontSize="small" />
                     </IconButton>
                     <IconButton
                       size="small"
                       onClick={() => handleDeleteUser(user.id)}
                       color="error"
                       disabled={user.id === 1}
                       title={user.id === 1 ? t('admin.cannotDeletePrimary') : t('admin.deleteUser')}
                     >
                       <Delete fontSize="small" />
                     </IconButton>
                   </TableCell>
                </TableRow>
              ))}
              {users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    {t('admin.noUsers')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
       )}

       </Box>

       {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>{t('admin.createNewUser')}</DialogTitle>
        <form onSubmit={handleCreateUser}>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label={t('admin.email')}
              type="email"
              fullWidth
              variant="outlined"
              value={newUserEmail}
              onChange={(e) => setNewUserEmail(e.target.value)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label={t('admin.password')}
              type="password"
              fullWidth
              variant="outlined"
              value={newUserPassword}
              onChange={(e) => setNewUserPassword(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateDialogOpen(false)}>
              {t('dialogs.cancel')}
            </Button>
            <Button type="submit" variant="contained" disabled={creating}>
              {creating ? <CircularProgress size={20} /> : t('admin.create')}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Container>
  );
}

export default AdminPage;
