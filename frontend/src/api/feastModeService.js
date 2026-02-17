import api from './axios';

// Add auth token interceptor if needed (assuming user_id is handled via token or session)
// For now, assuming simple endpoint calls. If user_id is needed in params, we'll add it.
// The backend uses dependency `get_current_user` or similar, usually via headers.

export const feastModeService = {
  /**
   * Get current Feast Mode status
   * @returns {Promise<{is_active: boolean, config: object|null, effective_targets: object}>}
   */
  getStatus: async () => {
    try {
      const response = await api.get('/feast-mode/status');
      return response.data;
    } catch (error) {
      console.error('Error fetching Feast Mode status:', error);
      throw error;
    }
  },

  /**
   * Propose a banking strategy for a future event
   * @param {string} eventName 
   * @param {string} eventDate (YYYY-MM-DD)
   * @param {number} [customDeduction] Optional custom deduction amount
   * @param {string[]} [selectedMeals] Optional list of meals to adjust
   * @returns {Promise<object>} Proposal details
   */
  proposeStrategy: async (eventName, eventDate, customDeduction = null, selectedMeals = null) => {
    try {
      const payload = {
        event_name: eventName,
        event_date: eventDate,
        custom_deduction: customDeduction,
        selected_meals: selectedMeals
      };
      const response = await api.post('/feast-mode/propose', payload);
      return response.data;
    } catch (error) {
      console.error('Error proposing Feast Mode strategy:', error);
      throw error;
    }
  },

  /**
   * Run a pre-check before activation
   * @param {string} startDate 
   * @param {number} dailyDeduction 
   * @returns {Promise<object>} Check results { warning, message, ... }
   */
  preActivateCheck: async (startDate, dailyDeduction) => {
    try {
      const payload = {
        start_date: startDate,
        daily_deduction: dailyDeduction
      };
      const response = await api.post('/feast-mode/pre-activate-check', payload);
      return response.data;
    } catch (error) {
      console.error('Error in pre-activate check:', error);
      throw error;
    }
  },

  /**
   * Activate Feast Mode
   * @param {object} proposal The proposal object returned from proposeStrategy
   * @param {boolean} [workoutBoost=true] Whether to enable workout boost
   * @returns {Promise<object>} Activated configuration
   */
  activate: async (proposal, workoutBoost = true) => {
    try {
      const payload = {
        ...proposal,
        workout_boost: workoutBoost
      };
      const response = await api.post('/feast-mode/activate', payload);
      return response.data;
    } catch (error) {
      console.error('Error activating Feast Mode:', error);
      throw error;
    }
  },

  /**
   * Cancel active Feast Mode
   * @returns {Promise<object>} Result message
   */
  cancel: async () => {
    try {
      const response = await api.post('/feast-mode/cancel');
      return response.data;
    } catch (error) {
      console.error('Error canceling Feast Mode:', error);
      throw error;
    }
  },

  /**
   * Get preview of deactivation consequences
   * @returns {Promise<object>} Preview details
   */
  getDeactivationPreview: async () => {
    try {
      const response = await api.post('/feast-mode/deactivate-preview');
      return response.data;
    } catch (error) {
      console.error('Error fetching deactivation preview:', error);
      throw error;
    }
  },

  /**
   * Update mid-day adjustments
   * @param {object} params { adjust_calories: number, completed_meals: string[] }
   * @returns {Promise<object>} Result message
   */
  updateMidDay: async (adjustCalories, completedMeals) => {
    try {
      const payload = {
        adjust_calories: adjustCalories,
        completed_meals: completedMeals
      };
      const response = await api.post('/feast-mode/update', payload);
      return response.data;
    } catch (error) {
      console.error('Error updating Feast Mode mid-day:', error);
      throw error;
    }
  },

  /**
   * Get overrides for a specific date
   * @param {string} date (YYYY-MM-DD)
   * @returns {Promise<object>} Map of meal_id -> override details
   */
  getOverrides: async (date) => {
    try {
      const response = await api.get(`/feast-mode/overrides?date=${date}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching Feast Mode overrides:', error);
      throw error;
    }
  }
};


export default feastModeService;
