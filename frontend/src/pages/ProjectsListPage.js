import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Button,
  TableSortLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  AlertTitle,
} from '@mui/material';
import { Visibility, Delete, Add, Person, ArrowBack } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { projectApi } from '../services/api';

const STATUS_COLORS = {
  pending: 'default',
  crawling: 'warning',
  parsing: 'info',
  analyzing: 'info',
  completed: 'success',
  stopped: 'error',
  failed: 'error',
};

function ProjectsListPage() {
  const { t } = useTranslation();
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [viewingUserId, setViewingUserId] = useState(null);

  // Check if we're viewing projects for a specific user (from admin panel)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const userId = params.get('user_id');
    if (userId) {
      setViewingUserId(parseInt(userId, 10));
    }
  }, [location.search]);

  const fetchProjects = async (params = {}) => {
    try {
      // Determine authentication method
      let requestParams = params;
      if (viewingUserId) {
        // Admin viewing user's projects - use admin key
        const adminKey = localStorage.getItem('admin_key');
        requestParams = {
          ...params,
          user_id: viewingUserId,
          admin_key: adminKey
        };
      } else if (!isAuthenticated) {
        // Guest user - use guest session token
        const guestToken = localStorage.getItem('guest_session_token');
        requestParams = {
          ...params,
          guest_session_token: guestToken
        };
      }
      const res = await projectApi.list(requestParams);
      setProjects(res.data);
    } catch (err) {
      if (err.response?.status === 401) {
        setError(t('errors.unauthorized'));
      } else {
        setError(err.response?.data?.detail || t('errors.failedToLoadProjects'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = {
      sort_by: sortBy,
      sort_order: sortOrder
    };
    fetchProjects(params);
  }, [sortBy, sortOrder, viewingUserId]);

  const handleDelete = async (projectId) => {
    if (!window.confirm(t('projects.confirmDelete'))) {
      return;
    }
    try {
      const guestToken = !isAuthenticated ? localStorage.getItem('guest_session_token') : null;
      await projectApi.delete(projectId, guestToken);
      setProjects(projects.filter((p) => p.id !== projectId));
    } catch (err) {
      setError(t('errors.failedToDeleteProject'));
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
        return t('status.pending');
      case 'crawling':
        return t('status.crawling');
      case 'parsing':
        return t('status.parsing');
      case 'analyzing':
        return t('status.analyzing');
      case 'completed':
        return t('status.completed');
      case 'stopped':
        return t('status.stopped');
      case 'failed':
        return t('status.failed');
      default:
        return status;
    }
  };

  const handleRequestSort = (field) => {
    let newSortOrder;
    if (sortBy === field) {
      // Toggle order if same field
      newSortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      // Default to ascending for new field
      newSortOrder = 'asc';
    }
    setSortBy(field);
    setSortOrder(newSortOrder);
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthSuccess('');
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
          // Refresh projects after successful auth
          fetchProjects({ sort_by: sortBy, sort_order: sortOrder });
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

  const openAuthDialog = (mode) => {
    setAuthMode(mode);
    setAuthDialogOpen(true);
    setAuthError('');
    setAuthSuccess('');
    setEmail('');
    setPassword('');
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

   // If not authenticated and not viewing admin's user projects, show login prompt
   if (!isAuthenticated && !viewingUserId) {
     return (
       <>
         <Container maxWidth="sm" sx={{ mt: 8 }}>
           <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
             <Person sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
             <Typography variant="h5" gutterBottom>
               {t('projects.loginRequired')}
             </Typography>
             <Typography variant="body2" color="text.secondary" paragraph>
               {t('projects.loginToViewProjects')}
             </Typography>
             <Button
               variant="contained"
               size="large"
               startIcon={<Person />}
               onClick={() => openAuthDialog('login')}
             >
               {t('home.login')}
             </Button>
           </Paper>
         </Container>

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
         </Dialog>
       </>
     );
   }

  return (
    <Container data-block="projects-list-container" maxWidth="lg" sx={{ mt: 8 }}>
      {viewingUserId && (
        <Alert 
          severity="info" 
          sx={{ mb: 3 }}
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<ArrowBack />}
              onClick={() => navigate('/projects')}
            >
              {t('admin.backToProjects')}
            </Button>
          }
        >
          <AlertTitle>{t('admin.projectsForUser')} #{viewingUserId}</AlertTitle>
          {t('admin.projectsForUser')} #{viewingUserId}
        </Alert>
      )}

      <Box data-block="projects-header" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mb: 3 }}>
          <Typography variant="h4">
            {viewingUserId ? `${t('admin.userProjects')} #${viewingUserId}` : t('projects.title')}
          </Typography>
          {!viewingUserId && (
            <Button
              data-block="new-analysis-button"
              variant="contained"
              startIcon={<Add />}
              onClick={() => navigate('/')}
            >
              {t('projects.newAnalysis')}
            </Button>
          )}
        </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

        <TableContainer data-block="projects-table" component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortBy === 'domain'}
                    direction={sortBy === 'domain' ? sortOrder : 'asc'}
                    onClick={() => handleRequestSort('domain')}
                  >
                    {t('projects.domain')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortBy === 'status'}
                    direction={sortBy === 'status' ? sortOrder : 'asc'}
                    onClick={() => handleRequestSort('status')}
                  >
                    {t('projects.status')}
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'created_at'}
                    direction={sortBy === 'created_at' ? sortOrder : 'asc'}
                    onClick={() => handleRequestSort('created_at')}
                  >
                    {t('projects.created')}
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">{t('projects.pages')}</TableCell>
                <TableCell align="right">{t('projects.foreignWords')}</TableCell>
                <TableCell align="center">{t('projects.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects.map((project) => (
                <TableRow
                  key={project.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/project/${project.id}`)}
                >
                  <TableCell>{project.domain}</TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusLabel(project.status)}
                      size="small"
                      color={STATUS_COLORS[project.status] || 'default'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {new Date(project.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell align="right">{project.stats?.total_pages || 0}</TableCell>
                  <TableCell align="right">{project.stats?.foreign_words_count || 0}</TableCell>
                  <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/project/${project.id}`)}
                      title={t('projects.view')}
                    >
                      <Visibility fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(project.id)}
                      title={t('projects.delete')}
                      color="error"
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {projects.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    {t('projects.noProjects')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        </Box>
      </Container>
    );
}

export default ProjectsListPage;