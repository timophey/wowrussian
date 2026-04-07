import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Typography,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Chip,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import { Add, Edit, Delete, Save } from '@mui/icons-material';
import MDEditor from '@uiw/react-md-editor';
import api from '../services/api';

function StaticPagesEditor({ adminKey, useTokenAuth }) {
  const { t, i18n } = useTranslation();
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingPage, setEditingPage] = useState(null);
  const [formData, setFormData] = useState({ url: '', lang: 'ru', title: '', content_md: '' });
  const [saving, setSaving] = useState(false);

  const effectiveKey = useTokenAuth ? null : adminKey;

  const fetchPages = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const config = { params: { limit: 1000 } };
      if (effectiveKey) {
        config.params.admin_key = effectiveKey;
      }
      const res = await api.get('/static-pages/', config);
      setPages(res.data.pages || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load pages');
    } finally {
      setLoading(false);
    }
  }, [effectiveKey]);

  useEffect(() => {
    fetchPages();
  }, [fetchPages]);

  const handleOpenEditor = (page = null) => {
    if (page) {
      setEditingPage(page);
      setFormData({
        url: page.url,
        lang: page.lang,
        title: page.title,
        content_md: page.content_md || '',
      });
    } else {
      setEditingPage(null);
      setFormData({ url: '', lang: 'ru', title: '', content_md: '' });
    }
    setEditorOpen(true);
    setError('');
    setSuccess('');
  };

  const handleCloseEditor = () => {
    setEditorOpen(false);
    setEditingPage(null);
    setFormData({ url: '', lang: 'ru', title: '', content_md: '' });
  };

  const handleSave = async () => {
    if (!formData.url.trim() || !formData.title.trim()) {
      setError('URL and title are required');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const config = {};
      if (effectiveKey) {
        config.params = { admin_key: effectiveKey };
      }
      if (editingPage) {
        await api.put(`/static-pages/${editingPage.id}`, {
          title: formData.title,
          content_md: formData.content_md,
        }, config);
        setSuccess('Page updated successfully');
      } else {
        await api.post('/static-pages/', {
          url: formData.url,
          lang: formData.lang,
          title: formData.title,
          content_md: formData.content_md,
        }, config);
        setSuccess('Page created successfully');
      }
      handleCloseEditor();
      fetchPages();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save page');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (pageId) => {
    if (!window.confirm('Are you sure you want to delete this page?')) {
      return;
    }
    setError('');
    setSuccess('');
    try {
      const config = {};
      if (effectiveKey) {
        config.params = { admin_key: effectiveKey };
      }
      await api.delete(`/static-pages/${pageId}`, config);
      setSuccess('Page deleted successfully');
      fetchPages();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete page');
    }
  };

  if (loading && pages.length === 0) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">{t('admin.staticPages.title', 'Static Pages')}</Typography>
        <Button
          variant="outlined"
          startIcon={<Add />}
          onClick={() => handleOpenEditor()}
        >
          {t('admin.staticPages.create', 'Create Page')}
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>URL</TableCell>
              <TableCell>Lang</TableCell>
              <TableCell>Title</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pages.map((page) => (
              <TableRow key={`${page.url}-${page.lang}`} hover>
                <TableCell>/{page.url}</TableCell>
                <TableCell>
                  <Chip label={page.lang} size="small" />
                </TableCell>
                <TableCell>{page.title}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => handleOpenEditor(page)}>
                    <Edit fontSize="small" />
                  </IconButton>
                  <IconButton size="small" color="error" onClick={() => handleDelete(page.id)}>
                    <Delete fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {pages.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  {t('admin.staticPages.noPages', 'No static pages yet')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Editor Dialog */}
      <Dialog open={editorOpen} onClose={handleCloseEditor} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingPage ? t('admin.staticPages.edit', 'Edit Page') : t('admin.staticPages.create', 'Create Page')}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            {!editingPage && (
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                  label="URL"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  fullWidth
                  helperText="e.g., legal-info, privacy-policy"
                  disabled={!!editingPage}
                />
                <FormControl sx={{ minWidth: 120 }}>
                  <InputLabel>Language</InputLabel>
                  <Select
                    value={formData.lang}
                    onChange={(e) => setFormData({ ...formData, lang: e.target.value })}
                    label="Language"
                    disabled={!!editingPage}
                  >
                    <MenuItem value="ru">Russian</MenuItem>
                    <MenuItem value="en">English</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            )}
            <TextField
              label="Title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              fullWidth
              sx={{ mb: 2 }}
            />
            <Typography variant="body2" gutterBottom>
              {t('admin.staticPages.content', 'Content (Markdown)')}
            </Typography>
            <div data-color-mode="light">
              <MDEditor
                value={formData.content_md}
                onChange={(value) => setFormData({ ...formData, content_md: value })}
                height={400}
                preview="live"
              />
            </div>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditor}>
            {t('dialogs.cancel', 'Cancel')}
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? t('admin.saving', 'Saving...') : t('admin.save', 'Save')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default StaticPagesEditor;
