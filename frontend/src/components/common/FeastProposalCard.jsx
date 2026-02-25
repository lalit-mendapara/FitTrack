import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Dumbbell, Flame, Ban, Check, ArrowRight, Activity } from 'lucide-react';

const FeastProposalCard = ({ proposal, onConfirm, onCancel, onBack, loading, isStatic = false }) => {
  if (!proposal) return null;

  // Local state for adjustments
  const [deduction, setDeduction] = useState(proposal.daily_deduction);
  const [workoutPref, setWorkoutPref] = useState('standard'); // standard, cardio, skip
  
  // Recalculate totals dynamically
  const totalBanked = deduction * proposal.days_remaining;
  const effectiveCalories = proposal.base_calories - deduction;

    const [isActivated, setIsActivated] = useState(false);
    const navigate = useNavigate();

  const handleConfirm = async () => {
      try {
        await onConfirm({
            ...proposal,
            daily_deduction: deduction,
            total_banked: totalBanked,
            workout_preference: workoutPref
        });
        setIsActivated(true);
      } catch (e) {
        // Parent handles toast
      }
  };

  const workoutOptions = [
      { id: 'standard', label: 'Standard', icon: <Flame size={14} />, desc: 'Depletion Workout' },
      { id: 'cardio', label: 'Cardio', icon: <ActivityIcon />, desc: 'Max Burn Focus' },
      { id: 'skip', label: 'Skip', icon: <Ban size={14} />, desc: 'No changes' },
  ];

  if (isActivated || isStatic) {
    // Use values from proposal (saved data) if static, or local state if just activated but not yet static'd (though logic handles both)
    // Actually, if static, proposal contains the FINAL values because we updated it in parent.
    // If just activated (local state), use deduction/workoutPref state.
    
    const displayDeduction = isStatic ? proposal.daily_deduction : deduction;
    const displayBanked = isStatic ? proposal.total_banked : totalBanked;
    const displayWorkout = isStatic ? proposal.workout_preference : workoutPref;

    const getAdjustingText = () => {
        if (!proposal.selected_meals || proposal.selected_meals.length === 0) return 'All Meals';
        return proposal.selected_meals.map(m => m.charAt(0).toUpperCase() + m.slice(1)).join(', ');
    };

    return (
         <div className="animate-in fade-in zoom-in bg-white p-6 rounded-xl border border-green-100 shadow-md w-full max-w-sm">
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center shrink-0">
                    <Check size={20} />
                </div>
                <div>
                     <h3 className="text-lg font-bold text-gray-900 leading-tight">Feast Mode Active</h3>
                </div>
            </div>

            <div className="space-y-3 bg-gray-50 p-4 rounded-xl border border-gray-100">
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-600 font-medium">Event</span>
                    <span className="text-gray-900 font-bold text-right max-w-[150px] truncate" title={proposal.event_name}>{proposal.event_name}</span>
                 </div>
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-600 font-medium">Date</span>
                    <span className="text-gray-900 font-bold">{proposal.event_date.split('T')[0]}</span>
                 </div>
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-600 font-medium">Adjusting</span>
                    <span className="text-gray-900 font-bold text-right max-w-[150px] truncate" title={getAdjustingText()}>{getAdjustingText()}</span>
                 </div>
                 <div className="flex justify-between items-center text-sm pt-2 border-t border-gray-200 mt-2">
                    <span className="text-gray-600 font-medium">Daily Reduction</span>
                    <span className="text-gray-900 font-bold">-{displayDeduction} kcal</span>
                 </div>
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-600 font-medium">Banked Calories</span>
                    <span className="text-green-600 font-bold">+{displayBanked} kcal</span>
                 </div>
                 <div className="flex justify-between items-center text-sm pt-2 border-t border-gray-200 mt-2">
                    <span className="text-gray-600 font-medium">Workout Focus</span>
                    <span className="text-indigo-600 font-bold capitalize">{displayWorkout || 'Standard'}</span>
                 </div>
            </div>

            {!isStatic && (
                <button 
                    onClick={() => navigate('/dashboard?tab=diet-plan')}
                    className="w-full mt-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
                >
                    Go to Diet Plan <ArrowRight size={16} />
                </button>
            )}
         </div>
    );
  }

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 bg-white p-4 rounded-xl border border-gray-200 shadow-sm w-full max-w-sm">
      <div className="text-center pb-2 border-b border-gray-100">
          <h3 className="text-lg font-bold text-gray-900">Feast Strategy</h3>
          <p className="text-xs text-gray-500">For {proposal.event_name} ({proposal.days_remaining} days away)</p>
      </div>

      <div className="space-y-4">
          {/* Calorie Slider */}
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
               <div className="flex justify-between items-center mb-2">
                   <label className="text-xs font-semibold text-gray-700">Daily Deficit</label>
                   <span className="text-xs font-bold text-red-500">-{deduction} kcal</span>
               </div>
               <input 
                  type="range" 
                  min="50" 
                  max="400" 
                  step="50" 
                  value={deduction} 
                  onChange={(e) => setDeduction(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
               />
               <div className="flex justify-between mt-1 text-[10px] text-gray-400">
                   <span>Min (50)</span>
                   <span>Max (400)</span>
               </div>
          </div>

          {/* Stats Summary */}
          <div className="grid grid-cols-2 gap-2">
              <div className="p-2 bg-indigo-50 rounded-lg border border-indigo-100 text-center">
                  <p className="text-[10px] text-indigo-500 uppercase font-bold">Total Banked</p>
                  <p className="text-lg font-bold text-indigo-700">{totalBanked}</p>
              </div>
              <div className="p-2 bg-green-50 rounded-lg border border-green-100 text-center">
                   <p className="text-[10px] text-green-500 uppercase font-bold">Daily Target</p>
                   <p className="text-lg font-bold text-green-700">{Math.round(effectiveCalories)}</p>
              </div>
          </div>

          {/* Workout Preference */}
          <div>
              <label className="block text-xs font-semibold text-gray-700 mb-2">Workout Adjustment</label>
              <div className="grid grid-cols-3 gap-2">
                  {workoutOptions.map((opt) => (
                      <button
                          key={opt.id}
                          onClick={() => setWorkoutPref(opt.id)}
                          className={`flex flex-col items-center justify-center p-2 rounded-lg border transition-all
                              ${workoutPref === opt.id 
                                  ? 'bg-gray-800 text-white border-gray-800 shadow-md transform scale-105' 
                                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                              }
                          `}
                      >
                          <div className={`mb-1 ${workoutPref === opt.id ? 'text-indigo-300' : 'text-gray-400'}`}>
                              {opt.icon}
                          </div>
                          <span className="text-[10px] font-bold">{opt.label}</span>
                          <span className="text-[9px] opacity-70 leading-tight">{opt.desc}</span>
                      </button>
                  ))}
              </div>
              
              {/* Dynamic Muscle Group Display */}
              <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Primary Muscle Group</span>
                  <span className="text-sm font-bold text-indigo-700">
                      {workoutPref === 'standard' && "Chest & Triceps"}
                      {workoutPref === 'cardio' && "Cardio & Core"}
                      {workoutPref === 'skip' && "Rest / Active Recovery"}
                  </span>
              </div>
          </div>
      </div>

      <div className="flex gap-2 pt-2 border-t border-gray-100 flex-col">
          {loading ? (
              <div className="space-y-2">
                  <div className="flex justify-between text-xs text-gray-500">
                      <span>Activating Feast Mode...</span>
                      <span>Please wait</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                      <div className="bg-indigo-600 h-2 rounded-full animate-progress-indeterminate origin-left"></div>
                  </div>
              </div>
          ) : (
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                    <button 
                        onClick={onCancel}
                        disabled={loading}
                        className="flex-1 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-transparent hover:border-gray-200"
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={onBack}
                        disabled={loading}
                        className="flex-1 py-2 bg-white border border-gray-200 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                        Back
                    </button>
                </div>
                <button 
                    onClick={handleConfirm}
                    disabled={loading}
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <span>Confirm Plan</span>
                    <Check size={14} />
                </button>
              </div>
          )}
      </div>
    </div>
  );
};

// Simple Icon component for Cardio
const ActivityIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
    </svg>
);

export default FeastProposalCard;
