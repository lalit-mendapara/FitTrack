
import api from '../api/axios';

/**
 * Meal Plan Service
 * Handles fetching and generating meal plans.
 */

export const getCurrentMealPlan = async () => {
    const response = await api.get('/meal-plans/current');
    return response.data;
};

export const generateMealPlan = async (customPrompt = null) => {
    const payload = customPrompt ? { custom_prompt: customPrompt } : {};
    const response = await api.post('/meal-plans/', payload);
    return response.data;
};

export const regenerateMealPlan = async () => {
    const response = await api.post('/meal-plans/regenerate');
    return response.data;
};
