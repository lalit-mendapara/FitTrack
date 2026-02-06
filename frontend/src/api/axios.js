import axios from 'axios';

// Create an axios instance
const api = axios.create({
  baseURL: '/api', // Vite proxy will handle forwarding to backend
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('diet_planner_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle errors globally if needed
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error:', error.response.data);
      
      // Optional: Handle 401 Unauthorized globally
      if (error.response.status === 401 || error.response.status === 403) {
        // e.g., redirect to login or clear auth state
        console.warn('Unauthorized/Forbidden access. Redirecting to login...');
        window.dispatchEvent(new CustomEvent('auth:logout'));
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
