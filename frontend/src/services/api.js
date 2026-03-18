import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Project API
export const projectApi = {
  create: (url) => api.post('/projects', { url }),
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  delete: (id) => api.delete(`/projects/${id}`),
  stop: (id) => api.post(`/projects/${id}/stop`),
};

// Page API
export const pageApi = {
  list: (projectId, status) => {
    const params = status ? { status } : {};
    return api.get(`/projects/${projectId}/pages`, { params });
  },
  get: (projectId, pageId) => api.get(`/projects/${projectId}/pages/${pageId}`),
  getHtml: (projectId, pageId) => api.get(`/projects/${projectId}/pages/${pageId}/html`),
  getText: (projectId, pageId) => api.get(`/projects/${projectId}/pages/${pageId}/text`),
};

// Stats API
export const statsApi = {
  get: (projectId) => api.get(`/stats/${projectId}`),
};

// Auth API (placeholder)
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (email, password) => api.post('/auth/register', { email, password }),
};

export default api;