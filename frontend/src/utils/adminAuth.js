import { jwtDecode } from 'jwt-decode';

const ADMIN_TOKEN_KEY = 'admin_token';
const ADMIN_USER_KEY = 'admin_user';

export const adminAuth = {
  setToken: (token) => {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  },

  getToken: () => {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  },

  setUser: (user) => {
    localStorage.setItem(ADMIN_USER_KEY, JSON.stringify(user));
  },

  getUser: () => {
    const user = localStorage.getItem(ADMIN_USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  isAuthenticated: () => {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);
    if (!token) return false;

    try {
      const decoded = jwtDecode(token);
      // Check if token is expired (exp is in seconds)
      if (decoded.exp * 1000 < Date.now()) {
        adminAuth.logout();
        return false;
      }
      return true;
    } catch (e) {
      console.error('Invalid token format:', e);
      adminAuth.logout();
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USER_KEY);
  },

  getAuthHeader: () => {
    if (!adminAuth.isAuthenticated()) {
      // If token is missing or expired, redirect automatically and clear state
      adminAuth.logout();
      window.location.replace('/admin/login');
      return {};
    }
    const token = adminAuth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
};
