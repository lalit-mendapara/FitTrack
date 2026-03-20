import React, { useState } from 'react';
import { X, Calendar, Flame, Activity, Loader2, PartyPopper } from 'lucide-react';
import feastModeService from '../../api/feastModeService';
import { toast } from 'react-toastify';
import { useDietPlan } from '../../hooks/useDietPlan';

const FeastActivateModal = ({ onClose, onSuccess }) => {
    const { plan: dietPlan } = useDietPlan();
    
    const [eventName, setEventName] = useState('');
    const [eventDate, setEventDate] = useState('');
    const [selectedMeals, setSelectedMeals] = useState([]);
    const [dailyDeduction, setDailyDeduction] = useState(250);
    const [workoutPref, setWorkoutPref] = useState('standard'); // standard, cardio
    
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 14);
    const maxDateStr = maxDate.toISOString().split('T')[0];

    // Options for meals
    const MEAL_OPTIONS = [
        { key: 'breakfast', label: 'Breakfast' },
        { key: 'lunch', label: 'Lunch' },
        { key: 'snacks', label: 'Snacks' }, 
        { key: 'dinner', label: 'Dinner' },
    ];

    const getMealCals = (mealKey) => {
        if (!dietPlan?.meal_plan) return 0;
        let meal;
        if (Array.isArray(dietPlan.meal_plan)) {
            meal = dietPlan.meal_plan.find(m => {
                const id = (m.meal_id || '').toLowerCase();
                const label = (m.label || '').toLowerCase();
                const key = mealKey.toLowerCase();
                return id === key || label === key || id.includes(key); 
            });
        } else {
            const key = mealKey.toLowerCase();
            meal = dietPlan.meal_plan[key] || dietPlan.meal_plan[key + 's'];
        }
        if (!meal) return 0;
        const n = meal.nutrients || {};
        const p = Number(n.p || n.protein || 0);
        const c = Number(n.c || n.carbs || 0);
        const f = Number(n.f || n.fat || 0);
        return Math.round((p * 4) + (c * 4) + (f * 9));
    };

    const toggleMeal = (meal) => {
        if (selectedMeals.includes(meal)) {
            setSelectedMeals(prev => prev.filter(m => m !== meal));
        } else {
            setSelectedMeals(prev => [...prev, meal]);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!eventName.trim()) {
            setError("Please enter an event name");
            return;
        }
        if (!eventDate) {
            setError("Please select a date");
            return;
        }
        
        const today = new Date();
        today.setHours(0,0,0,0);
        const selected = new Date(eventDate);
        selected.setHours(0,0,0,0);
        const diffDays = Math.ceil((selected - today) / (1000 * 60 * 60 * 24));
        
        if (diffDays <= 0) {
            setError("Event must be in the future");
            return;
        }
        if (diffDays > 14) {
            setError("Event cannot be more than 14 days away");
            return;
        }

        setLoading(true);
        setError('');

        try {
            // 1. Get the strategy proposal
            const finalMeals = selectedMeals.length > 0 ? selectedMeals : null;
            const proposal = await feastModeService.proposeStrategy(eventName, eventDate, dailyDeduction, finalMeals);
            
            // 2. Overwrite proposal fields that might be adjustable
            const finalPayload = {
                ...proposal,
                daily_deduction: dailyDeduction,
                total_banked: dailyDeduction * proposal.days_remaining,
                workout_preference: workoutPref
            };

            // 3. Activate immediately
            await feastModeService.activate(finalPayload, true);
            toast.success("Feast Mode activated successfully!");
            onSuccess();
        } catch (err) {
            console.error(err);
            toast.error(err.response?.data?.detail || "Failed to activate Feast Mode.");
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-9999 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in">
            <div className={`bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col max-h-screen ${loading ? 'pointer-events-none' : ''}`}>
                
                {loading && (
                    <div className="absolute inset-0 bg-white/80 backdrop-blur-md z-10 flex flex-col items-center justify-center">
                        <Loader2 size={48} className="text-indigo-600 animate-spin mb-4" />
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Generating Feast Plan...</h3>
                        <p className="text-gray-500 text-sm font-medium">Please wait while we update your diet and workout plans.</p>
                    </div>
                )}

                {/* Header */}
                <div className="bg-linear-to-r from-indigo-600 to-purple-600 p-4 shrink-0 flex items-center justify-between text-white">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <PartyPopper size={20} />
                        </div>
                        <h2 className="font-bold text-lg">Activate Feast Mode</h2>
                    </div>
                    {!loading && (
                        <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-lg transition-colors">
                            <X size={24} />
                        </button>
                    )}
                </div>

                {/* Body scrollable content */}
                <div className="p-5 overflow-y-auto custom-scrollbar flex-1 relative">
                    <form id="feast-activate-form" onSubmit={handleSubmit} className="space-y-6">
                        
                        {/* Event Details */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-gray-700 mb-1">Event Name</label>
                                <input
                                    type="text"
                                    placeholder="e.g. Birthday Party"
                                    value={eventName}
                                    onChange={(e) => { setEventName(e.target.value); setError(''); }}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-700 mb-1">Event Date</label>
                                <div className="relative">
                                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                    <input
                                        type="date"
                                        value={eventDate}
                                        onChange={(e) => { setEventDate(e.target.value); setError(''); }}
                                        className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        min={new Date().toISOString().split('T')[0]}
                                        max={maxDateStr}
                                        required
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Daily Deduction */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <label className="text-sm font-bold text-gray-700">Daily Calories Deduction</label>
                                <span className="text-sm font-black text-red-500">-{dailyDeduction} kcal/day</span>
                            </div>
                            <input 
                                type="range" 
                                min="50" 
                                max="400" 
                                step="50" 
                                value={dailyDeduction} 
                                onChange={(e) => setDailyDeduction(Number(e.target.value))}
                                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                            />
                            <div className="flex justify-between mt-1 text-xs text-gray-400 font-medium font-mono">
                                <span>50 kcal</span>
                                <span>Max 400 kcal</span>
                            </div>
                        </div>

                        {/* Meals to Adjust */}
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Meals to Adjust</label>
                            <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded-xl border border-gray-100">
                                {MEAL_OPTIONS.map((opt) => {
                                    const cals = getMealCals(opt.key);
                                    const isChecked = selectedMeals.includes(opt.key);
                                    return (
                                        <div key={opt.key} className="flex items-center justify-between col-span-2 sm:col-span-1 border-b sm:border-b-0 border-gray-100 pb-2 sm:pb-0">
                                            <label className="flex items-center gap-2 cursor-pointer w-full">
                                                <input 
                                                    type="checkbox" 
                                                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                                                    checked={isChecked}
                                                    onChange={() => toggleMeal(opt.key)}
                                                />
                                                <div className="flex flex-col">
                                                    <span className={`text-sm ${isChecked ? 'text-gray-900 font-bold' : 'text-gray-600 font-medium'}`}>
                                                        {opt.label}
                                                    </span>
                                                    <span className="text-xs text-gray-400 font-medium">{cals} kcal</span>
                                                </div>
                                            </label>
                                        </div>
                                    );
                                })}
                            </div>
                            <p className="text-xs text-gray-500 mt-2 font-medium">
                                {selectedMeals.length === 0 
                                    ? "* Tip: Leave blank to deduct calories evenly across all meals." 
                                    : "* Calories will only be deducted from selected meals."}
                            </p>
                        </div>

                        {/* Workout Adjustments */}
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Workout Adjustments</label>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    type="button"
                                    onClick={() => setWorkoutPref('standard')}
                                    className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all
                                        ${workoutPref === 'standard' 
                                            ? 'bg-indigo-50 border-indigo-600 text-indigo-800 ring-1 ring-indigo-600 shadow-md' 
                                            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                                        }
                                    `}
                                >
                                    <Flame size={20} className={workoutPref === 'standard' ? 'text-indigo-600 mb-1' : 'text-gray-400 mb-1'} />
                                    <span className="text-sm font-bold">Standard</span>
                                    <span className="text-xs opacity-70 text-center">Depletion Workout</span>
                                </button>
                                
                                <button
                                    type="button"
                                    onClick={() => setWorkoutPref('cardio')}
                                    className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all
                                        ${workoutPref === 'cardio' 
                                            ? 'bg-indigo-50 border-indigo-600 text-indigo-800 ring-1 ring-indigo-600 shadow-md' 
                                            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                                        }
                                    `}
                                >
                                    <Activity size={20} className={workoutPref === 'cardio' ? 'text-indigo-600 mb-1' : 'text-gray-400 mb-1'} />
                                    <span className="text-sm font-bold">Cardio</span>
                                    <span className="text-xs opacity-70 text-center">Max Burn Focus</span>
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                                <p className="text-sm text-red-600 font-bold text-center">{error}</p>
                            </div>
                        )}

                    </form>
                </div>

                {/* Footer Action */}
                <div className="p-4 border-t border-gray-100 bg-gray-50 shrink-0">
                    <button
                        type="submit"
                        form="feast-activate-form"
                        disabled={loading}
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-base rounded-xl shadow-lg transition-transform active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {loading ? 'Generative Feast Plan...' : 'Generate Feast Plan'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FeastActivateModal;
