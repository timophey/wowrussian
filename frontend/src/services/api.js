import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('access_token');
};

// Set auth token
const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      // Clear token and redirect to home
      setAuthToken(null);
      window.location.href = '/';
      return Promise.reject(error);
    }
    
    return Promise.reject(error);
  }
);

// Project API
export const projectApi = {
  create: (url, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.post('/projects', { url }, { params });
  },
  list: (params = {}) => api.get('/projects', { params }),
  get: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/projects/${id}`, { params });
  },
  delete: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.delete(`/projects/${id}`, { params });
  },
  stop: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.post(`/projects/${id}/stop`, {}, { params });
  },
  start: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.post(`/projects/${id}/start`, {}, { params });
  },
  clearPages: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.delete(`/projects/${id}/pages`, { params });
  },
};

// Page API
export const pageApi = {
  list: (projectId, params = {}) => api.get(`/projects/${projectId}/pages`, { params }),
  get: (projectId, pageId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/projects/${projectId}/pages/${pageId}`, { params });
  },
  getHtml: (projectId, pageId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/projects/${projectId}/pages/${pageId}/html`, { params });
  },
  getText: (projectId, pageId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/projects/${projectId}/pages/${pageId}/text`, { params });
  },
};

// Stats API
export const statsApi = {
  get: (projectId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/stats/${projectId}`, { params });
  },
};

// Auth API
export const authApi = {
  login: (email, password) => {
    const data = new URLSearchParams();
    data.append('username', email);
    data.append('password', password);
    return api.post('/auth/login', data, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },
  register: (email, password) => api.post('/auth/register', { email, password }),
  getCurrentUser: () => api.get('/auth/me'),
  logout: () => {
    setAuthToken(null);
  },
};

// Admin API
export const adminApi = {
  listUsers: (adminKey) => api.get('/admin/users', { params: { admin_key: adminKey } }),
  createUser: (email, password, adminKey) => api.post('/admin/users', { email, password }, { params: { admin_key: adminKey } }),
  deleteUser: (userId, adminKey) => api.delete(`/admin/users/${userId}`, { params: { admin_key: adminKey } }),
};

// Guest Session API
export const guestApi = {
  createSession: () => api.post('/guest/sessions'),
  validateSession: (token) => api.get(`/guest/sessions/${token}`),
};

// Single Analysis API
export const singleApi = {
  check: (url) => api.post('/single/check', { url }, {
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  }),
};

export default api;