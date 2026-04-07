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
    
    // Skip 401 handling for login and register requests - let the auth context handle these errors
    const isAuthRequest = originalRequest.url?.includes('/auth/login') ||
                          originalRequest.url?.includes('/auth/register');
    
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthRequest) {
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
  resume: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.post(`/projects/${id}/resume`, {}, { params });
  },
  clearPages: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.delete(`/projects/${id}/pages`, { params });
  },
  // Whitelist API
  getWhitelist: (id, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/projects/${id}/whitelist`, { params });
  },
  addToWhitelist: (id, words, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.post(`/projects/${id}/whitelist`, { words }, { params });
  },
  removeFromWhitelist: (id, wordId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.delete(`/projects/${id}/whitelist/${wordId}`, { params });
  },
  // Async export
  startAsyncExport: (id, language, guestSessionToken, timezone) => {
    const params = new URLSearchParams();
    params.append('language', language);
    params.append('timezone', timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
    if (guestSessionToken) {
      params.append('guest_session_token', guestSessionToken);
    }
    return api.post(`/projects/${id}/export-xlsx/async`, {}, { params });
  },
   getExportJobStatus: (jobId, guestSessionToken) => {
     const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
     return api.get(`/projects/export-jobs/${jobId}`, { params });
   },
   cancelExportJob: (jobId, guestSessionToken) => {
     const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
     return api.post(`/projects/export-jobs/${jobId}/cancel`, {}, { params });
   },
   downloadExportFile: (jobId, guestSessionToken) => {
     const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
     return api.get(`/projects/export-jobs/${jobId}/download`, {
       params,
       responseType: 'blob',
     });
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
  getUniqueForeignWords: (projectId, guestSessionToken) => {
    const params = guestSessionToken ? { guest_session_token: guestSessionToken } : {};
    return api.get(`/stats/${projectId}/unique-foreign-words`, { params });
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
  deleteAccount: () => api.post('/auth/me/delete-account'),
  changePassword: (currentPassword, newPassword) => api.post('/auth/me/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  }),
};

// Admin API
export const adminApi = {
  listUsers: (adminKey) => {
    const token = localStorage.getItem('access_token');
    const config = adminKey ? { params: { admin_key: adminKey } } : {};
    if (token) {
      config.headers = { Authorization: `Bearer ${token}` };
    }
    return api.get('/admin/users', config);
  },
  createUser: (email, password, adminKey) => {
    const token = localStorage.getItem('access_token');
    const config = adminKey ? { params: { admin_key: adminKey } } : {};
    if (token) {
      config.headers = { Authorization: `Bearer ${token}` };
    }
    return api.post('/admin/users', { email, password }, config);
  },
  deleteUser: (userId, adminKey) => {
    const token = localStorage.getItem('access_token');
    const config = adminKey ? { params: { admin_key: adminKey } } : {};
    if (token) {
      config.headers = { Authorization: `Bearer ${token}` };
    }
    return api.delete(`/admin/users/${userId}`, config);
  },
  updateUserRole: (userId, role, adminKey) => {
    const token = localStorage.getItem('access_token');
    const config = adminKey ? { params: { admin_key: adminKey } } : {};
    if (token) {
      config.headers = { Authorization: `Bearer ${token}` };
    }
    return api.patch(`/admin/users/${userId}/role`, { role }, config);
  },
  getUserProjects: (userId, adminKey) => {
    const token = localStorage.getItem('access_token');
    const config = adminKey ? { params: { admin_key: adminKey } } : {};
    if (token) {
      config.headers = { Authorization: `Bearer ${token}` };
    }
    return api.get(`/admin/users/${userId}/projects`, config);
  },
  migrateAdminRole: (adminKey) => {
    return api.post('/admin/migrate-admin-role', {}, { params: { admin_key: adminKey } });
  },
};

// Guest Session API
export const guestApi = {
  createSession: () => api.post('/guest/sessions'),
  validateSession: (token) => api.get(`/guest/sessions/${token}`),
  deleteSession: (token) => api.post('/auth/guest/delete-session', null, { params: { session_token: token } }),
};

// Single Analysis API
export const singleApi = {
  check: (url) => api.post('/single/check', { url }, {
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  }),
  checkText: (text) => api.post('/single/check-text', { text }, {
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  }),
  checkFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/single/check-file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
  },
  getConfig: () => api.get('/single/config'),
};

export default api;