
import api from '../api/axios';

/**
 * Workout Service
 * Handles Workout Preferences and Workout Plans.
 */

// --- Preferences ---
export const getDoWorkoutPreferencesExist = async () => {
    try {
        await api.get('/workout-preferences/me');
        return true;
    } catch (err) {
        if (err.response && err.response.status === 404) {
            return false;
        }
        throw err;
    }
};

export const getWorkoutPreferences = async () => {
    const response = await api.get('/workout-preferences/me');
    return response.data;
};

export const saveWorkoutPreferences = async (prefsData) => {
    // Check if exists first to decide PUT vs POST or backend handles it?
    // Usually backend handles insert-or-update or we adhere to specific endpoints
    // The current backend seems to handle creation via the generate endpoint or dedicated create endpoint?
    // Looking at backend/app/api/workout_preferences.py (implied existence), 
    // Usually we update via POST/PUT. Assuming /workout-preferences/
    const response = await api.post('/workout-preferences/', prefsData);
    return response.data;
};

// --- Plans ---
export const getCurrentWorkoutPlan = async () => {
    const response = await api.get('/workout-plans/current');
    return response.data;
};

export const generateWorkoutPlan = async (workoutPreferences, customPrompt = null, options = {}) => {
    // The backend expects a wrapper object: { workout_request: { ... } } or flattened?
    // Checking backend schemas/workout_plan.py: 
    // class WorkoutPlanRequest(BaseModel): workout_request: WorkoutPlanRequestData
    // class WorkoutPlanRequestData(BaseModel): user_id (optional), workout_preferences, custom_prompt, ignore_history
    
    // So payload structure:
    const payload = {
        workout_request: {
            // user_id is inferred from token on backend usually
            workout_preferences: workoutPreferences,
            custom_prompt: customPrompt,
            ignore_history: options.ignore_history || false
        }
    };
    
    const response = await api.post('/workout-plans/generate', payload);
    return response.data;
};
