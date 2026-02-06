import axios from './axios';

/**
 * Get unread notifications.
 * @returns {Promise<Array>}
 */
export const getUnreadNotifications = async () => {
    try {
        const response = await axios.get('/notifications/unread');
        return response.data;
    } catch (error) {
        console.error("Error fetching notifications:", error);
        return [];
    }
};

/**
 * Mark notification as read.
 * @param {number} notificationId 
 */
export const markNotificationRead = async (notificationId) => {
    try {
        await axios.post(`/notifications/${notificationId}/read`);
    } catch (error) {
        console.error("Error marking notification read:", error);
    }
};
