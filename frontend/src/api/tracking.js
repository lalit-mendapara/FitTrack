import axios from './axios';

/**
 * Log a meal to the backend.
 * @param {Object} mealData - { meal_name, meal_type, calories, protein, carbs, fat }
 */
export const logMeal = async (mealData) => {
    try {
        const response = await axios.post('/tracking/log-meal', mealData);
        return response.data;
    } catch (error) {
        console.error("Error logging meal:", error);
        throw error;
    }
};

/**
 * Log a workout to the backend.
 * @param {Object} workoutData - { exercise_name, duration_min?, calories_burned? }
 */
export const logWorkout = async (workoutData) => {
    try {
        const response = await axios.post('/tracking/log-workout', workoutData);
        return response.data;
    } catch (error) {
        console.error("Error logging workout:", error);
        throw error;
    }
};

/**
 * Log a workout session duration.
 * @param {Object} sessionData - { date, duration_minutes }
 */
export const logWorkoutSession = async (sessionData) => {
    try {
        const response = await axios.post('/tracking/log-workout-session', sessionData);
        return response.data;
    } catch (error) {
        console.error("Error logging workout session:", error);
        throw error;
    }
};
/**
 * Delete a meal log.
 * @param {number} logId 
 */
export const deleteMealLog = async (logId) => {
    try {
        await axios.delete(`/tracking/log-meal/${logId}`);
    } catch (error) {
         console.error("Error deleting meal log:", error);
         throw error;
    }
};

/**
 * Delete a workout log.
 * @param {number} logId 
 */
export const deleteWorkoutLog = async (logId) => {
    try {
        await axios.delete(`/tracking/log-workout/${logId}`);
    } catch (error) {
         console.error("Error deleting workout log:", error);
         throw error;
    }
};

/**
 * Delete all diet logs for a specific date (defaults to today).
 * @param {string} date - ISO date string (YYYY-MM-DD)
 */
export const deleteDailyDietLogs = async (date) => {
    try {
        const params = date ? { date } : {};
        await axios.delete('/tracking/daily-diet', { params });
    } catch (error) {
         console.error("Error deleting daily diet logs:", error);
         throw error;
    }
};

/**
 * Delete all workout logs for a specific date (defaults to today).
 * @param {string} date - ISO date string (YYYY-MM-DD)
 */
export const deleteDailyWorkoutLogs = async (date) => {
    try {
        const params = date ? { date } : {};
        await axios.delete('/tracking/daily-workout', { params });
    } catch (error) {
         console.error("Error deleting daily workout logs:", error);
         throw error;
    }
};

/**
 * Delete ALL workout logs and sessions.
 */
export const deleteAllWorkoutLogs = async () => {
    try {
        await axios.delete('/tracking/all-workout');
    } catch (error) {
         console.error("Error deleting all workout logs:", error);
         throw error;
    }
};

/**
 * Fetch diet logs for a specific date (defaults to today).
 * Returns meals array and calories_target.
 * @param {string} date - ISO date string (YYYY-MM-DD)
 * @returns {Promise<{calories_target: number, meals: Array}>}
 */
export const getDailyDietLogs = async (date) => {
    try {
        const params = date ? { date } : {};
        const response = await axios.get('/tracking/daily-diet', { params });
        return response.data;
    } catch (error) {
        console.error("Error fetching daily diet logs:", error);
        throw error;
    }
};

/**
 * Fetch workout logs for a specific date (defaults to today).
 * @param {string} date - ISO date string (YYYY-MM-DD)
 * @returns {Promise<{workouts: Array}>}
 */
export const getDailyWorkoutLogs = async (date) => {
    try {
        const params = date ? { date } : {};
        const response = await axios.get('/tracking/daily-workout', { params });
        return response.data;
    } catch (error) {
        console.error("Error fetching daily workout logs:", error);
        throw error;
    }
};

/**
 * Fetch weekly workout overview.
 * @returns {Promise<Object>}
 */
export const getWeeklyWorkoutOverview = async () => {
    try {
        const response = await axios.get('/tracking/weekly-workout');
        return response.data;
    } catch (error) {
        console.error("Error fetching weekly workout overview:", error);
        throw error;
    }
};
