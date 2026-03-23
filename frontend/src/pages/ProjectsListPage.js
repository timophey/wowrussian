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
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Button,
  TableSortLabel,
} from '@mui/material';
import { Visibility, Delete, Add } from '@mui/icons-material';
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
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const fetchProjects = async (params = {}) => {
    try {
      const res = await projectApi.list(params);
      setProjects(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('errors.failedToLoadProjects'));
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
  }, [sortBy, sortOrder]);

  const handleDelete = async (projectId) => {
    if (!window.confirm(t('projects.confirmDelete'))) {
      return;
    }
    try {
      await projectApi.delete(projectId);
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

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">{t('projects.title')}</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/')}
        >
          {t('projects.newAnalysis')}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
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
                <TableCell align="right">{project.stats?.total_pages || 0}</TableCell>
                <TableCell align="right">{project.stats?.foreign_words_count || 0}</TableCell>
                <TableCell align="right">
                  {new Date(project.created_at).toLocaleDateString()}
                </TableCell>
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
    </Container>
  );
}

export default ProjectsListPage;