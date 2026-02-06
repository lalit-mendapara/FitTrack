import React, { useState, useEffect } from 'react';
import api from '../../api/axios';
import { toast } from 'react-toastify';
import { Dumbbell, Activity, Calendar, Clock, AlertCircle } from 'lucide-react';

const UnifiedProfileForm = ({ existingProfile, existingPreferences, onSuccess, onUpdateStart, onUpdateEnd }) => {
    // Combined Initial State
    const [formData, setFormData] = useState({
        // Profile Data
        weight: existingProfile?.weight || '',
        height: existingProfile?.height || '',
        weight_goal: existingProfile?.weight_goal || '',
        fitness_goal: existingProfile?.fitness_goal || 'maintenance',
        activity_level: existingProfile?.activity_level || 'moderate',
        country: existingProfile?.country || 'India',
        diet_type: existingProfile?.diet_type || 'veg',
        
        // Workout Preferences Data
        experience_level: existingPreferences?.experience_level || 'beginner',
        days_per_week: existingPreferences?.days_per_week || 3,
        session_duration_min: existingPreferences?.session_duration_min || 30,
        health_restrictions: existingPreferences?.health_restrictions || ''
    });

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Weight validation constants
    const MIN_WEIGHT = 35;
    const MAX_WEIGHT = 130;

    useEffect(() => {
        // Sync if props change significantly (optional, mostly for update mode)
        if (existingProfile || existingPreferences) {
            setFormData(prev => ({
                ...prev,
                ...(existingProfile || {}),
                ...(existingPreferences || {})
            }));
        }
    }, [existingProfile, existingPreferences]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
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
            setFormData(prev => ({ ...prev, fitness_goal: availableGoals[0].value }));
        }
    }, [formData.weight, formData.weight_goal]);


    // State to toggle workout section
    const [includeWorkout, setIncludeWorkout] = useState(!!existingPreferences);

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
        if (onUpdateStart) onUpdateStart();
        setError('');

        try {
             // 1. Save/Update User Profile
             const profilePayload = {
                weight: parseFloat(formData.weight),
                height: parseFloat(formData.height),
                weight_goal: parseFloat(formData.weight_goal),
                fitness_goal: formData.fitness_goal,
                activity_level: formData.activity_level,
                country: formData.country,
                diet_type: formData.diet_type
             };

             if (existingProfile) {
                await api.put('/user-profiles/me', profilePayload);
             } else {
                await api.post('/user-profiles/', profilePayload);
             }

             // 2. Save/Update Workout Preferences (Only if toggled ON)
             if (includeWorkout) {
                 const preferencesPayload = {
                     experience_level: formData.experience_level,
                     days_per_week: parseInt(formData.days_per_week),
                     session_duration_min: parseInt(formData.session_duration_min),
                     health_restrictions: formData.health_restrictions
                 };

                 await api.post('/workout-preferences/', preferencesPayload);
             }

             toast.success("Profile Saved Successfully!");
             if (onSuccess) onSuccess(includeWorkout ? 'all' : 'physical'); 

        } catch (err) {
            console.error("Unified Update Failed", err);
            let errorMsg = "Failed to save profile. Please try again.";
            
            if (err.response?.data?.detail) {
                const detail = err.response.data.detail;
                if (typeof detail === 'string') {
                    errorMsg = detail;
                } else if (Array.isArray(detail)) {
                    // Handle Pydantic validation errors (array of objects)
                    errorMsg = detail.map(e => `${e.loc[e.loc.length-1]}: ${e.msg}`).join(', ');
                } else if (typeof detail === 'object') {
                    errorMsg = JSON.stringify(detail);
                }
            }
            
            setError(errorMsg);
            toast.error("Failed to save profile.");
        } finally {
            setIsLoading(false);
            if (onUpdateEnd) onUpdateEnd();
        }
    };

    return (
        <div className="bg-white p-8 rounded-3xl shadow-xl w-full max-w-5xl mx-auto border border-gray-100">
             <div className="mb-10 text-center">
                <h2 className="text-3xl font-black text-gray-900 bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
                   {existingProfile ? 'Update Your Profile' : 'Let\'s Get Started'}
                </h2>
                <p className="text-gray-500 mt-3 text-lg font-medium">
                  We need a few details to build your perfect diet and workout plan.
                </p>
             </div>

             <form onSubmit={handleSubmit} className="space-y-12">
                 {error && (
                    <div className="bg-red-50 text-red-600 p-4 rounded-xl text-sm text-center border border-red-100 font-semibold flex items-center justify-center gap-2">
                        <AlertCircle size={18} />
                        {error}
                    </div>
                 )}

                 {/* SECTION 1: PHYSICAL STATS */}
                 <div>
                     <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2 border-b border-gray-100 pb-2">
                        <span className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600">
                            <Activity size={18} />
                        </span>
                        Physical Stats
                     </h3>
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Current Weight (kg)</label>
                            <input
                                type="number"
                                name="weight"
                                required
                                step="0.1"
                                value={formData.weight}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                                placeholder="e.g. 75"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Height (cm)</label>
                            <input
                                type="number"
                                name="height"
                                required
                                step="0.1"
                                value={formData.height}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                                placeholder="e.g. 175"
                            />
                        </div>
                         <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Goal Weight (kg)</label>
                            <input
                                type="number"
                                name="weight_goal"
                                required
                                step="0.1"
                                value={formData.weight_goal}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                                placeholder="e.g. 70"
                            />
                        </div>
                     </div>
                 </div>

                 {/* SECTION 2: DIET & LIFESTYLE */}
                 <div>
                    <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2 border-b border-gray-100 pb-2">
                        <span className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center text-green-600">
                            <span className="text-lg">🥗</span>
                        </span>
                        Diet & Lifestyle
                     </h3>
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Fitness Goal</label>
                            <select
                                name="fitness_goal"
                                value={formData.fitness_goal}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                            >
                                {getAvailableFitnessGoals().map(goal => (
                                    <option key={goal.value} value={goal.value}>{goal.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Activity Level</label>
                            <select
                                name="activity_level"
                                value={formData.activity_level}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                            >
                                <option value="sedentary">Sedentary (Little/No Exercise)</option>
                                <option value="light">Light (1-3 days/week)</option>
                                <option value="moderate">Moderate (3-5 days/week)</option>
                                <option value="active">Active (6-7 days/week)</option>
                                <option value="extra_active">Extra Active (Physical Job)</option>
                            </select>
                        </div>
                         <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Country</label>
                            <select
                                name="country"
                                value={formData.country}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
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
                            <label className="block text-sm font-bold text-gray-700 mb-2">Diet Preference</label>
                            <select
                                name="diet_type"
                                value={formData.diet_type}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                            >
                                <option value="veg">Vegetarian</option>
                                <option value="non_veg">Non-Vegetarian</option>
                                <option value="both">Veg + Non-Veg (Both)</option>
                            </select>
                        </div>
                     </div>
                 </div>

                 {/* SECTION 3: WORKOUT PREFERENCES (Optional) */}
                  <div className={`transition-all duration-300 ${!includeWorkout ? 'opacity-80' : ''}`}>
                    <div className="flex items-center justify-between mb-6 border-b border-gray-100 pb-2">
                        <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                            <span className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center text-purple-600">
                                <Dumbbell size={18} />
                            </span>
                            Workout Preferences
                        </h3>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <span className="text-sm font-semibold text-gray-600">Setup Workout Plan?</span>
                             <div className="relative inline-block w-12 h-6 rounded-full transition-colors duration-200 ease-in-out bg-gray-200 has-[:checked]:bg-indigo-600">
                                <input 
                                    type="checkbox" 
                                    className="peer sr-only"
                                    checked={includeWorkout}
                                    onChange={(e) => setIncludeWorkout(e.target.checked)}
                                />
                                <span className="absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-200 ease-in-out peer-checked:translate-x-6 shadow-sm"></span>
                             </div>
                        </label>
                    </div>
                     
                     {includeWorkout && (
                         <div className="space-y-8 animate-in fade-in slide-in-from-top-4 duration-300">
                             {/* Experience Level */}
                            <div>
                                <label className="block text-sm font-bold text-gray-700 mb-3">Experience Level</label>
                                <div className="grid grid-cols-3 gap-4">
                                    {['beginner', 'intermediate', 'advanced'].map((level) => (
                                        <button
                                            key={level}
                                            type="button"
                                            onClick={() => setFormData(prev => ({ ...prev, experience_level: level }))}
                                            className={`py-3 px-4 rounded-xl capitalize transition-all border-2 font-bold ${
                                                formData.experience_level === level
                                                ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm'
                                                : 'border-gray-200 bg-white hover:border-indigo-200 text-gray-500'
                                            }`}
                                        >
                                            {level}
                                        </button>
                                    ))}
                                </div>
                            </div>

                             <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                 {/* Frequency */}
                                 <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-3 flex justify-between">
                                        <span>Days Per Week</span>
                                        <span className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs">
                                            {formData.days_per_week} Days
                                        </span>
                                    </label>
                                    <input
                                        type="range"
                                        min="1"
                                        max="7"
                                        name="days_per_week"
                                        value={formData.days_per_week}
                                        onChange={handleChange}
                                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                    />
                                    <div className="flex justify-between text-xs text-gray-400 mt-2 font-medium">
                                        <span>1 Day</span>
                                        <span>7 Days</span>
                                    </div>
                                 </div>

                                 {/* Duration */}
                                 <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-3">Session Duration (Mins)</label>
                                    <div className="relative">
                                        <Clock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18}/>
                                        <input
                                            type="number"
                                            min="10"
                                            step="5"
                                            name="session_duration_min"
                                            value={formData.session_duration_min}
                                            onChange={handleChange}
                                            className="w-full pl-12 pr-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white"
                                        />
                                    </div>
                                 </div>
                             </div>
                            
                             {/* Restrictions */}
                            <div>
                                <label className="block text-sm font-bold text-gray-700 mb-2">Health Restrictions (Optional)</label>
                                <textarea
                                    name="health_restrictions"
                                    rows="3"
                                    value={formData.health_restrictions}
                                    onChange={handleChange}
                                    placeholder="Any injuries, joint pain, or limitations we should know about?"
                                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all bg-gray-50/50 hover:bg-white resize-none"
                                />
                            </div>

                         </div>
                     )}
                     {!includeWorkout && (
                         <div className="p-6 bg-gray-50 border border-gray-200 border-dashed rounded-xl text-center text-gray-500 text-sm">
                             Workout preferences can be added later if you wish to generate a workout plan.
                         </div>
                     )}
                  </div>

                 <div className="pt-8">
                    <button
                        type="submit"
                        disabled={isLoading}
                        className={`w-full py-4 px-6 rounded-2xl shadow-xl shadow-indigo-200 text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 font-bold text-xl transition-all transform hover:-translate-y-1 active:scale-95 ${isLoading ? 'opacity-80 cursor-wait' : ''}`}
                    >
                        {isLoading ? 'Saving...' : (includeWorkout ? 'Save All Preferences' : 'Save Physical Profile')}
                    </button>
                    <p className="text-center text-sm text-gray-400 mt-4 font-medium">
                        {includeWorkout 
                            ? "Clicking this will setup both your Diet and Workout plans." 
                            : "Clicking this will only setup your Diet plan."}
                    </p>
                 </div>

             </form>
        </div>
    );
};

export default UnifiedProfileForm;
