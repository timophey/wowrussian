import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';
import i18n from '../i18n';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Helper function to translate backend error messages
const translateAuthError = (detail, fallbackKey) => {
  if (!detail) {
    return i18n.t(`errors.${fallbackKey}`);
  }
  
  const lowerDetail = detail.toLowerCase();
  
  // Map backend error messages to i18n keys
  if (lowerDetail.includes('incorrect email or password') || lowerDetail.includes('could not validate credentials')) {
    return i18n.t('errors.invalidCredentials');
  }
  if (lowerDetail.includes('already registered') || lowerDetail.includes('already exists')) {
    return i18n.t('errors.emailAlreadyExists');
  }
  if (lowerDetail.includes('password') && lowerDetail.includes('8')) {
    return i18n.t('errors.weakPassword');
  }
  
  // Default fallback
  return i18n.t(`errors.${fallbackKey}`);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token');
    if (token) {
      authApi.getCurrentUser()
        .then(response => {
          if (response?.data) {
            setUser(response.data);
          } else {
            authApi.logout();
          }
        })
        .catch(() => {
          authApi.logout();
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authApi.login(email, password);
      const token = response.data.access_token;
      localStorage.setItem('access_token', token);
      const currentUserResponse = await authApi.getCurrentUser();
      setUser(currentUserResponse.data);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: translateAuthError(error.response?.data?.detail, 'loginFailed')
      };
    }
  };

  const register = async (email, password) => {
    try {
      await authApi.register(email, password);
      // Auto-login after registration
      const loginResult = await login(email, password);
      return loginResult;
    } catch (error) {
      return {
        success: false,
        error: translateAuthError(error.response?.data?.detail, 'registrationFailed')
      };
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
