import axios from './axios';

/**
 * Update user timezone.
 * @param {string} timezone - e.g. "Asia/Kolkata"
 */
export const updateTimezone = async (timezone) => {
    try {
        await axios.patch('/user-profiles/timezone', { timezone });
    } catch (error) {
        console.error("Error updating timezone:", error);
    }
};

/**
 * Get current user profile.
 */
export const getMyProfile = async () => {
    try {
        const response = await axios.get('/user-profiles/me');
        return response.data;
    } catch (error) {
        console.error("Error fetching profile:", error);
        throw error;
    }
};
