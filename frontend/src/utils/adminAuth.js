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
    return !!localStorage.getItem(ADMIN_TOKEN_KEY);
  },

  logout: () => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USER_KEY);
  },

  getAuthHeader: () => {
    const token = adminAuth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
};
