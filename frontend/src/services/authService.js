
import api from '../api/axios';

/**
 * Authentication Service
 * Handles API calls for Auth logic.
 */

export const loginUser = async (email, password) => {
    const formData = new FormData();
    formData.append('username', email); // OAuth2PasswordRequestForm expects username
    formData.append('password', password);
    const response = await api.post('/login/token', formData);
    return response.data;
};

export const registerUser = async (userData) => {
    const response = await api.post('/users/', userData);
    return response.data;
};

export const logoutUser = async () => {
    return api.post('/login/logout');
};

export const verifySession = async () => {
    const response = await api.get('/users/me');
    return response.data; // Helper to check if token is valid
};
