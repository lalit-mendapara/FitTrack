import React, { useState, useEffect } from 'react';
import api from '../../api/axios';
import { toast } from 'react-toastify';


const ProfileForm = ({ existingData, onSuccess, onUpdateStart, onUpdateEnd }) => {
  const [formData, setFormData] = useState({
    weight: existingData?.weight || '',
    height: existingData?.height || '',
    weight_goal: existingData?.weight_goal || '',
    fitness_goal: existingData?.fitness_goal || 'maintenance',
    activity_level: existingData?.activity_level || 'moderate',
    country: existingData?.country || 'India',
    diet_type: existingData?.diet_type || 'veg',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Weight validation constants
  const MIN_WEIGHT = 35;
  const MAX_WEIGHT = 130;

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Handle number inputs
    if (['weight', 'height', 'weight_goal'].includes(name)) {
        if (value === '' || (!isNaN(value) && Number(value) >= 0)) {
             setFormData(prev => ({ ...prev, [name]: value }));
        }
    } else {
        setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  // Weight validation helper
  const validateWeight = (weight, fieldName) => {
    const w = parseFloat(weight);
    if (!weight || isNaN(w)) return null;
    if (w < MIN_WEIGHT) return `${fieldName} must be at least ${MIN_WEIGHT}kg`;
    if (w > MAX_WEIGHT) return `${fieldName} must not exceed ${MAX_WEIGHT}kg`;
    return null;
  };

  // Determine which fitness goals to show based on weight comparison
  const currentWeight = parseFloat(formData.weight) || 0;
  const goalWeight = parseFloat(formData.weight_goal) || 0;

  // Case 1: Need to gain weight (current < goal) -> Muscle Gain, Maintenance
  const isGainWeightNeeded = currentWeight > 0 && goalWeight > 0 && currentWeight < goalWeight;
  
  // Case 2: Need to lose weight (current > goal) -> Weight Loss, Fat Loss, Maintenance
  const isWeightLossNeeded = currentWeight > 0 && goalWeight > 0 && currentWeight > goalWeight;
  
  // Case 3: At goal weight (current == goal) -> Maintenance only
  const isAtGoalWeight = currentWeight > 0 && goalWeight > 0 && currentWeight === goalWeight;

  // Get available fitness goals based on weight comparison
  const getAvailableFitnessGoals = () => {
    if (isAtGoalWeight) {
      return [{ value: 'maintenance', label: 'Maintenance' }];
    }
    if (isGainWeightNeeded) {
      return [
        { value: 'muscle_gain', label: 'Muscle Gain' },
        { value: 'maintenance', label: 'Maintenance' }
      ];
    }
    if (isWeightLossNeeded) {
      return [
        { value: 'weight_loss', label: 'Weight Loss' },
        { value: 'fat_loss', label: 'Fat Loss' },
        { value: 'maintenance', label: 'Maintenance' }
      ];
    }
    // Default: show all if weights not set
    return [
      { value: 'weight_loss', label: 'Weight Loss' },
      { value: 'fat_loss', label: 'Fat Loss' },
      { value: 'muscle_gain', label: 'Muscle Gain' },
      { value: 'maintenance', label: 'Maintenance' }
    ];
  };

  // Auto-correct fitness goal if it becomes invalid due to weight changes
  useEffect(() => {
    const availableGoals = getAvailableFitnessGoals();
    const currentGoalValid = availableGoals.some(g => g.value === formData.fitness_goal);
    
    if (!currentGoalValid && availableGoals.length > 0) {
      // Default to first available option
      setFormData(prev => ({ ...prev, fitness_goal: availableGoals[0].value }));
    }
  }, [formData.weight, formData.weight_goal]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate weights before submission
    const weightError = validateWeight(formData.weight, 'Current weight');
    const goalWeightError = validateWeight(formData.weight_goal, 'Goal weight');
    
    if (weightError) {
      toast.error(weightError);
      return;
    }
    if (goalWeightError) {
      toast.error(goalWeightError);
      return;
    }
    
    setIsLoading(true);
    if (onUpdateStart) onUpdateStart(); // Trigger global block
    setError('');

    try {
      // Prepare payload - convert numbers
      const payload = {
        ...formData,
        weight: parseFloat(formData.weight),
        height: parseFloat(formData.height),
        weight_goal: parseFloat(formData.weight_goal),
      };

      if (existingData) {
        await api.put('/user-profiles/me', payload);
        toast.success("User profile is updated");
      } else {
        await api.post('/user-profiles/', payload);
        toast.success("Physical profile is saved");
      }
      
      onSuccess(); // Callback to refresh parent data
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to save profile.');
    } finally {
      setIsLoading(false);
      if (onUpdateEnd) onUpdateEnd(); // specific finish trigger if needed immediately, though profile refresh might trigger re-render
    }
  };

  return (
    <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-4xl mx-auto h-full flex flex-col">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold text-gray-900">
          {existingData ? 'Update Profile' : 'Create Your Profile'}
        </h2>
        <p className="text-gray-500 mt-2">
          Let's get to know you better to build the perfect plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 flex flex-col flex-1">
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm text-center border border-red-100">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Physical Stats Section */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">Physical Stats</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  name="weight"
                  required
                  step="0.1"
                  value={formData.weight}
                  onChange={handleChange}
                  className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                  placeholder="e.g. 75"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm)</label>
                <input
                  type="number"
                  name="height"
                  required
                  step="0.1"
                  value={formData.height}
                  onChange={handleChange}
                  className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                  placeholder="e.g. 175"
                />
              </div>
            </div>

             <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Target Weight (kg)</label>
                <input
                  type="number"
                  name="weight_goal"
                  required
                  step="0.1"
                  value={formData.weight_goal}
                  onChange={handleChange}
                  className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                  placeholder="e.g. 70"
                />
              </div>
          </div>

          {/* Goals & Lifestyle Section */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">Goals & Lifestyle</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fitness Goal</label>
              <select
                name="fitness_goal"
                value={formData.fitness_goal}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
              >
                {getAvailableFitnessGoals().map(goal => (
                  <option key={goal.value} value={goal.value}>{goal.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Activity Level</label>
              <select
                name="activity_level"
                value={formData.activity_level}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
              >
                <option value="sedentary">Sedentary (Little/No Exercise)</option>
                <option value="light">Light (Exercise 1-3 days/week)</option>
                <option value="moderate">Moderate (Exercise 3-5 days/week)</option>
                <option value="active">Active (Exercise 6-7 days/week)</option>
                <option value="extra_active">Extra Active (Physical Job/Training)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Preferences Section */}
        <div className="space-y-6">
             <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">Your Preferences</h3>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
                  <select
                    name="country"
                    value={formData.country}
                    onChange={handleChange}
                    className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                  >
                    <option value="India">India</option>
                    <option value="USA">USA</option>
                    <option value="UK">UK</option>
                    <option value="Canada">Canada</option>
                    <option value="Australia">Australia</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Diet Preference</label>
                  <select
                    name="diet_type"
                    value={formData.diet_type}
                    onChange={handleChange}
                    className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                  >
                    <option value="veg">Vegetarian</option>
                    <option value="non_veg">Non-Vegetarian</option>
                  </select>
                </div>
             </div>
        </div>

        <div className="pt-6 mt-auto">
          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 px-6 border border-transparent rounded-xl shadow-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 font-bold text-lg transition-all transform hover:-translate-y-1 ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {isLoading ? 'Saving Profile...' : (existingData ? 'Update Profile' : 'Create Profile')}
          </button>
        </div>
      </form>
  </div>
  );
};

export default ProfileForm;
