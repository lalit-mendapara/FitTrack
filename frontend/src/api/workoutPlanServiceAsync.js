/**
 * Async Workout Plan Service with Task Polling
 * Replaces blocking HTTP requests with task-based polling
 */
import api from './axios';

/**
 * Start async workout plan generation
 * @param {Object} workoutRequest - Workout plan request data
 * @returns {Promise<{task_id: string, status: string, message: string}>}
 */
export const generateWorkoutPlanAsync = async (workoutRequest) => {
    const response = await api.post('/workout-plans/generate-async', {
        workout_request: workoutRequest
    });
    return response.data;
};

/**
 * Poll task status
 * @param {string} taskId - Celery task ID
 * @returns {Promise<{task_id: string, status: string, progress: number, message: string, result: object, error: string}>}
 */
export const getTaskStatus = async (taskId) => {
    const response = await api.get(`/workout-plans/status/${taskId}`);
    return response.data;
};

/**
 * Cancel a running task
 * @param {string} taskId - Celery task ID
 * @returns {Promise<{task_id: string, status: string, message: string}>}
 */
export const cancelTask = async (taskId) => {
    const response = await api.delete(`/workout-plans/cancel/${taskId}`);
    return response.data;
};

/**
 * Poll task until completion with exponential backoff
 * @param {string} taskId - Celery task ID
 * @param {Function} onProgress - Callback for progress updates (progress, message)
 * @param {number} maxAttempts - Maximum polling attempts (default: 60)
 * @returns {Promise<object>} - Final workout plan result
 */
export const pollTaskUntilComplete = async (taskId, onProgress = null, maxAttempts = 60) => {
    let attempts = 0;
    let delay = 1000; // Start with 1 second
    const maxDelay = 5000; // Max 5 seconds between polls
    
    while (attempts < maxAttempts) {
        try {
            const status = await getTaskStatus(taskId);
            
            // Update progress callback
            if (onProgress && status.progress !== undefined) {
                onProgress(status.progress, status.message || 'Processing...');
            }
            
            // Check terminal states
            if (status.status === 'SUCCESS') {
                if (onProgress) onProgress(100, 'Complete!');
                return status.result;
            }
            
            if (status.status === 'FAILURE') {
                throw new Error(status.error || 'Task failed');
            }
            
            // Task still processing - wait and retry
            await new Promise(resolve => setTimeout(resolve, delay));
            
            // Exponential backoff (1s -> 2s -> 3s -> 5s max)
            delay = Math.min(delay + 1000, maxDelay);
            attempts++;
            
        } catch (error) {
            if (error.response?.status === 404) {
                throw new Error('Task not found. It may have expired.');
            }
            throw error;
        }
    }
    
    throw new Error('Task polling timeout. Generation is taking longer than expected.');
};

/**
 * Generate workout plan with automatic polling (convenience wrapper)
 * @param {Object} workoutRequest - Workout plan request data
 * @param {Function} onProgress - Progress callback (progress, message)
 * @returns {Promise<object>} - Generated workout plan
 */
export const generateWorkoutPlanWithPolling = async (workoutRequest, onProgress = null) => {
    // Start task
    const { task_id } = await generateWorkoutPlanAsync(workoutRequest);
    
    // Poll until complete
    const result = await pollTaskUntilComplete(task_id, onProgress);
    
    return result;
};
