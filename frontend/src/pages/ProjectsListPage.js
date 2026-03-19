import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
      setError(err.response?.data?.detail || 'Failed to load projects');
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
    if (!window.confirm('Are you sure you want to delete this project?')) {
      return;
    }
    try {
      await projectApi.delete(projectId);
      setProjects(projects.filter((p) => p.id !== projectId));
    } catch (err) {
      setError('Failed to delete project');
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'crawling':
        return 'Crawling';
      case 'parsing':
        return 'Parsing';
      case 'analyzing':
        return 'Analyzing';
      case 'completed':
        return 'Completed';
      case 'stopped':
        return 'Stopped';
      case 'failed':
        return 'Failed';
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
        <Typography variant="h4">Projects</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/')}
        >
          New Analysis
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
                  Domain
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortBy === 'status'}
                  direction={sortBy === 'status' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('status')}
                >
                  Status
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortBy === 'created_at'}
                  direction={sortBy === 'created_at' ? sortOrder : 'asc'}
                  onClick={() => handleRequestSort('created_at')}
                >
                  Created
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">Pages</TableCell>
              <TableCell align="right">Foreign Words</TableCell>
              <TableCell align="center">Actions</TableCell>
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
                    title="View"
                  >
                    <Visibility fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(project.id)}
                    title="Delete"
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
                  No projects yet. Create one to get started!
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