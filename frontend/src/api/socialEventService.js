import api from './axios';

export const getActiveSocialEvent = async () => {
    try {
        const response = await api.get('/social-events/active');
        return response.data;
    } catch (error) {
        console.error("Failed to fetch active social event", error);
        return null;
    }
};
