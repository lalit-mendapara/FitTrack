import React, { useState } from 'react';
import { Calendar } from 'lucide-react';
import feastLogo from '../../images/Feast-logo98_png586.png';

const FeastSetupCard = ({ onSubmit, onCancel, dietPlan }) => {
  const [eventName, setEventName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [selectedMeals, setSelectedMeals] = useState([]);
  const [error, setError] = useState('');

  // Helper to compute max date (14 days from now)
  const maxDate = new Date();
  maxDate.setDate(maxDate.getDate() + 14);
  const maxDateStr = maxDate.toISOString().split('T')[0];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!eventName.trim()) {
      setError("Please enter an event name");
      return;
    }
    if (!eventDate) {
      setError("Please select a date");
      return;
    }
    
    // Basic validation: Date must be in future, max 14 days
    const today = new Date();
    today.setHours(0,0,0,0);
    const selected = new Date(eventDate);
    selected.setHours(0,0,0,0);
    
    const diffTime = selected - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays <= 0) {
      setError("Event must be in the future");
      return;
    }
    if (diffDays > 14) {
      setError("Event cannot be more than 14 days away");
      return;
    }

    // Pass selectedMeals (if empty, backend interprets as 'all')
    onSubmit({ eventName, eventDate, selectedMeals: selectedMeals.length > 0 ? selectedMeals : null });
  };

  const toggleMeal = (meal) => {
    if (selectedMeals.includes(meal)) {
      setSelectedMeals(prev => prev.filter(m => m !== meal));
    } else {
      setSelectedMeals(prev => [...prev, meal]);
    }
  };

  const getMealCals = (mealKey) => {
    if (!dietPlan?.meal_plan) return 0;
    
    let meal;
    if (Array.isArray(dietPlan.meal_plan)) {
        // Find by meal_id or label (case-insensitive)
        meal = dietPlan.meal_plan.find(m => {
            const id = (m.meal_id || '').toLowerCase();
            const label = (m.label || '').toLowerCase();
            const key = mealKey.toLowerCase();
            return id === key || label === key || id.includes(key); 
        });
    } else {
        // Legacy object usage
        const key = mealKey.toLowerCase();
        meal = dietPlan.meal_plan[key] || dietPlan.meal_plan[key + 's'];
    }
    
    if (!meal) return 0;
    
    const n = meal.nutrients || {};
    // Handle both {p, c, f} and {protein, carbs, fat}
    const p = Number(n.p || n.protein || 0);
    const c = Number(n.c || n.carbs || 0);
    const f = Number(n.f || n.fat || 0);
    return Math.round((p * 4) + (c * 4) + (f * 9));
  };

  const MEAL_OPTIONS = [
    { key: 'breakfast', label: 'Breakfast' },
    { key: 'lunch', label: 'Lunch' },
    { key: 'snacks', label: 'Snacks' }, // Assuming 'snack' covers snacks in plan logic or is mapped
    { key: 'dinner', label: 'Dinner' },
  ];

  return (
    <div className="bg-white p-5 rounded-xl border border-indigo-100 shadow-sm animate-in fade-in slide-in-from-bottom-2 space-y-4 max-w-sm w-full">
      <div className="flex items-center gap-3 border-b border-indigo-50 pb-3">
        <div className="p-2 bg-indigo-100 rounded-lg">
          <img src={feastLogo} alt="Feast Mode" className="h-5 w-5 object-contain" />
        </div>
        <div>
           <h3 className="font-bold text-gray-800">Plan Feast Mode</h3>
           <p className="text-xs text-gray-500">Bank calories for a big event</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Event Name</label>
          <input
            type="text"
            placeholder="e.g. Birthday Dinner"
            value={eventName}
            onChange={(e) => { setEventName(e.target.value); setError(''); }}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            autoFocus
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Event Date</label>
          <div className="relative">
             <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
             <input
                type="date"
                value={eventDate}
                onChange={(e) => { setEventDate(e.target.value); setError(''); }}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                min={new Date().toISOString().split('T')[0]}
                max={maxDateStr}
              />
          </div>
          <p className="text-[10px] text-gray-400 mt-1 ml-1">Event must be within next 14 days</p>
        </div>

        {/* Meal Selection Section */}
        <div>
            <label className="block text-xs font-semibold text-gray-700 mb-2">Meals to Adjust</label>
            <div className="space-y-2 bg-gray-50 p-3 rounded-lg border border-gray-100">
                {MEAL_OPTIONS.map((opt) => {
                    const cals = getMealCals(opt.key);
                    const isChecked = selectedMeals.includes(opt.key);
                    return (
                        <div key={opt.key} className="flex items-center justify-between">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input 
                                    type="checkbox" 
                                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                                    checked={isChecked}
                                    onChange={() => toggleMeal(opt.key)}
                                />
                                <span className={`text-sm ${isChecked ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                                    {opt.label}
                                </span>
                            </label>
                            <span className="text-xs text-gray-400 font-medium">{cals} kcal</span>
                        </div>
                    );
                })}
            </div>
            <p className="text-[10px] text-gray-400 mt-1 ml-1">
                {selectedMeals.length === 0 
                    ? "Adjustments spread evenly across all meals" 
                    : "Only selected meals will be reduced"}
            </p>
        </div>

        {error && <p className="text-xs text-red-500 font-medium">{error}</p>}

        <div className="flex gap-2 pt-2">
           <button
             type="button"
             onClick={onCancel}
             className="flex-1 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
           >
             Cancel
           </button>
           <button
             type="submit"
             className="flex-[2] py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-md transition-colors"
           >
             Check Strategy
           </button>
        </div>
      </form>
    </div>
  );
};

export default FeastSetupCard;
