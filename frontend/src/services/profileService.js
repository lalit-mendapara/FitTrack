
import api from '../api/axios';

/**
 * Profile Service
 * Handles fetching and updating user physical profiles.
 */

export const getProfile = async () => {
    const response = await api.get('/user-profiles/me');
    return response.data;
};

export const updateProfile = async (profileData) => {
    // profileData should match the expected schema
    const response = await api.put('/user-profiles/me', profileData);
    return response.data;
};

export const createProfile = async (profileData) => {
    const response = await api.post('/user-profiles/', profileData);
    return response.data;
};

export const checkProfileExists = async () => {
    try {
        await getProfile();
        return true;
    } catch (err) {
        if (err.response && err.response.status === 404) {
            return false;
        }
        throw err;
    }
};
