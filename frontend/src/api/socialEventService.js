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

export const cancelSocialEvent = async () => {
    try {
        const response = await api.post('/social-events/cancel');
        return response.data;
    } catch (error) {
        console.error("Failed to cancel social event", error);
        throw error;
    }
};

export const skipMeal = async (mealId, redistributeTo = null, isFeastDay = false) => {
    const response = await api.post('/meal-plans/skip-meal', {
        meal_id: mealId,
        redistribute_to: redistributeTo,
        is_feast_day: isFeastDay,
    });
    return response.data;
};
