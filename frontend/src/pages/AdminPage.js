import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
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
  Chip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
} from '@mui/material';
import { Add, Delete, ArrowBack, Visibility, Edit, Person, AdminPanelSettings, Settings as SettingsIcon } from '@mui/icons-material';
import { adminApi, projectApi } from '../services/api';
import StaticPagesEditor from '../components/StaticPagesEditor';
import useDocumentTitle from '../hooks/useDocumentTitle';

function AdminPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('admin.adminPanel'));
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user: currentUser, isAuthenticated: isUserAuthenticated } = useAuth();
  
  // State for admin key authentication (legacy)
  const [adminKey, setAdminKey] = useState('');
  const [isKeyAuthenticated, setIsKeyAuthenticated] = useState(false);
  
  // Check if user is admin via role
  const isAdmin = isUserAuthenticated && currentUser?.role === 'admin';
  
  // Use either JWT token or admin key
  const useTokenAuth = isAdmin;
  const effectiveAdminKey = useTokenAuth ? null : adminKey;
  
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [creating, setCreating] = useState(false);
  
  // Role editing state
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingRole, setEditingRole] = useState('');
  
  // User projects dialog
  const [userProjectsOpen, setUserProjectsOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userProjects, setUserProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  
  // Check for user_id in URL (for viewing specific user's projects)
  const urlUserId = searchParams.get('user_id');

  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // Check if admin key is stored or if user has admin role
  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    } else {
      const storedKey = localStorage.getItem('admin_key');
      if (storedKey) {
        setAdminKey(storedKey);
        setIsKeyAuthenticated(true);
        fetchUsers(storedKey);
      }
    }
  }, [isAdmin, currentUser]);

  const fetchUsers = async (key) => {
    setLoading(true);
    setError('');
    try {
      const res = await adminApi.listUsers(key);
      setUsers(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToLoadUsers'));
      if (!useTokenAuth) {
        setIsKeyAuthenticated(false);
        localStorage.removeItem('admin_key');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyLogin = (e) => {
    e.preventDefault();
    if (!adminKey.trim()) {
      setError(t('admin.enterAdminKey'));
      return;
    }
    localStorage.setItem('admin_key', adminKey);
    setIsKeyAuthenticated(true);
    fetchUsers(adminKey);
  };

  const handleKeyLogout = () => {
    localStorage.removeItem('admin_key');
    setAdminKey('');
    setIsKeyAuthenticated(false);
    setUsers([]);
  };

  const handleMigrateToRoleAdmin = async () => {
    if (!window.confirm('Convert admin key access to role-based admin? This will give the first user the admin role.')) {
      return;
    }
    try {
      await adminApi.migrateAdminRole(adminKey);
      setSuccess('Admin role migrated successfully. Please log in with your credentials.');
      handleKeyLogout();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to migrate admin role');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUserEmail.trim() || !newUserPassword.trim()) {
      setError(t('admin.fillAllFields'));
      return;
    }
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await adminApi.createUser(newUserEmail, newUserPassword, effectiveAdminKey);
      setCreateDialogOpen(false);
      setNewUserEmail('');
      setNewUserPassword('');
      fetchUsers(effectiveAdminKey);
      setSuccess(t('admin.userCreated'));
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
    setError('');
    setSuccess('');
    try {
      await adminApi.deleteUser(userId, effectiveAdminKey);
      fetchUsers(effectiveAdminKey);
      setSuccess(t('admin.userDeleted'));
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToDeleteUser'));
    }
  };

  const handleStartEditRole = (userId, currentRole) => {
    setEditingUserId(userId);
    setEditingRole(currentRole);
  };

  const handleCancelEditRole = () => {
    setEditingUserId(null);
    setEditingRole('');
  };

  const handleSaveRole = async (userId) => {
    setError('');
    setSuccess('');
    try {
      await adminApi.updateUserRole(userId, editingRole, effectiveAdminKey);
      fetchUsers(effectiveAdminKey);
      setEditingUserId(null);
      setEditingRole('');
      setSuccess(t('admin.roleUpdated'));
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToUpdateRole'));
    }
  };

  const handleViewUserProjects = async (user) => {
    setSelectedUser(user);
    setUserProjectsOpen(true);
    setProjectsLoading(true);
    setError('');
    try {
      const res = await adminApi.getUserProjects(user.id, effectiveAdminKey);
      setUserProjects(res.data.projects || []);
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.failedToLoadUserProjects'));
    } finally {
      setProjectsLoading(false);
    }
  };

  // If not authenticated via role and not via key, show login form
  if (!isAdmin && !isKeyAuthenticated) {
    return (
      <Container data-block="admin-login-container" maxWidth="sm" sx={{ mt: 8 }}>
        <Paper data-block="admin-login-form" elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom>
            {t('admin.adminPanel')}
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {t('admin.adminDescription')}
          </Typography>
          <form onSubmit={handleKeyLogin}>
            <TextField
              data-block="admin-key-input"
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
              data-block="login-button"
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
    <Container data-block="admin-panel-container" maxWidth="lg" sx={{ mt: 8 }}>
      <Box data-block="admin-panel-header" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mb: 3, flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h4">{t('admin.adminPanel')}</Typography>
            {isAdmin && (
              <Chip icon={<AdminPanelSettings />} label="Role-based Admin" color="success" size="small" />
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            {isAdmin && (
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => navigate('/profile')}
              >
                {t('profile.title')}
              </Button>
            )}
            {!isAdmin && (
              <Button
                variant="outlined"
                onClick={handleMigrateToRoleAdmin}
                startIcon={<Person />}
              >
                Migrate to Role
              </Button>
            )}
            <Button
              data-block="create-user-button"
              variant="outlined"
              startIcon={<Add />}
              onClick={() => setCreateDialogOpen(true)}
            >
              {t('admin.createUser')}
            </Button>
            <Button
              data-block="back-to-projects-button"
              variant="text"
              startIcon={<ArrowBack />}
              onClick={() => navigate('/projects')}
            >
              {t('admin.backToProjects')}
            </Button>
            {!isAdmin && (
              <Button
                data-block="logout-button"
                variant="text"
                color="error"
                onClick={handleKeyLogout}
              >
                {t('admin.logout')}
              </Button>
            )}
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2, width: '100%' }}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mb: 2, width: '100%' }}>
            {success}
          </Alert>
        )}

        {/* Tabs for Users and Static Pages */}
        <Tabs value={activeTab} onChange={(e, val) => setActiveTab(val)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={t('admin.users', 'Users')} />
          <Tab label={t('admin.staticPages', 'Static Pages')} />
        </Tabs>

        {/* Users Tab */}
        {activeTab === 0 && (
          loading ? (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer data-block="users-table" component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>{t('admin.userId')}</TableCell>
                  <TableCell>{t('admin.email')}</TableCell>
                  <TableCell>{t('admin.role')}</TableCell>
                  <TableCell>{t('admin.createdAt')}</TableCell>
                  <TableCell align="right">{t('admin.actions')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id} hover>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      {editingUserId === user.id ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <FormControl size="small" sx={{ minWidth: 100 }}>
                            <Select
                              value={editingRole}
                              onChange={(e) => setEditingRole(e.target.value)}
                            >
                              <MenuItem value="user">User</MenuItem>
                              <MenuItem value="admin">Admin</MenuItem>
                            </Select>
                          </FormControl>
                          <IconButton size="small" onClick={() => handleSaveRole(user.id)} color="success">
                            <Edit fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={handleCancelEditRole} color="default">
                            <Delete fontSize="small" />
                          </IconButton>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={user.role === 'admin' ? 'Admin' : 'User'}
                            color={user.role === 'admin' ? 'primary' : 'default'}
                            size="small"
                          />
                          <IconButton
                            size="small"
                            onClick={() => handleStartEditRole(user.id, user.role)}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Box>
                      )}
                    </TableCell>
                    <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleViewUserProjects(user)}
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
                    <TableCell colSpan={5} align="center">
                      {t('admin.noUsers')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          )
        )}

        {/* Static Pages Tab */}
        {activeTab === 1 && (
          <Paper sx={{ p: 3 }}>
            <StaticPagesEditor adminKey={adminKey} useTokenAuth={useTokenAuth} />
          </Paper>
        )}
      </Box>

      {/* Create User Dialog */}
      <Dialog data-block="create-user-dialog" open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
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

      {/* View User Projects Dialog */}
      <Dialog 
        open={userProjectsOpen} 
        onClose={() => setUserProjectsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {t('admin.userProjects')}: {selectedUser?.email}
        </DialogTitle>
        <DialogContent>
          {projectsLoading ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : userProjects.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
              {t('admin.noUserProjects')}
            </Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>{t('projects.domain')}</TableCell>
                    <TableCell>{t('projects.status')}</TableCell>
                    <TableCell>{t('projects.created')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {userProjects.map((project) => (
                    <TableRow key={project.id} hover>
                      <TableCell>{project.id}</TableCell>
                      <TableCell>{project.domain}</TableCell>
                      <TableCell>
                        <Chip 
                          label={t(`status.${project.status}`)} 
                          size="small"
                          color={project.status === 'completed' ? 'success' : project.status === 'failed' ? 'error' : 'default'}
                        />
                      </TableCell>
                      <TableCell>{new Date(project.created_at).toLocaleDateString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserProjectsOpen(false)}>
            {t('dialogs.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default AdminPage;
