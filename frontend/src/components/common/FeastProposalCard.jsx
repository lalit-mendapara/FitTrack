import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Dumbbell, Flame, Ban, Check, ArrowRight, Activity } from 'lucide-react';

const FeastProposalCard = ({ proposal, onConfirm, onCancel, loading }) => {
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

  if (isActivated) {
    return (
         <div className="animate-in fade-in zoom-in bg-white p-6 rounded-xl border border-green-100 shadow-md w-full max-w-sm text-center">
            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <Check size={24} />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Feast Mode Ready!</h3>
            <p className="text-sm text-gray-500 mb-4">Your plan has been updated.</p>
            <button 
                onClick={() => navigate('/dashboard?tab=diet-plan')}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
            >
                Go to Diet Plan <ArrowRight size={16} />
            </button>
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
                  max="1000" 
                  step="50" 
                  value={deduction} 
                  onChange={(e) => setDeduction(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
               />
               <div className="flex justify-between mt-1 text-[10px] text-gray-400">
                   <span>Min (50)</span>
                   <span>Max (1000)</span>
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
          </div>
      </div>

      <div className="flex gap-2 pt-2 border-t border-gray-100">
          <button 
              onClick={onCancel}
              className="flex-1 py-2 bg-white border border-gray-200 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
              Back
          </button>
          <button 
              onClick={handleConfirm}
              disabled={loading}
              className="flex-[2] py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-md transition-all flex items-center justify-center gap-2"
          >
              {loading ? 'Activating...' : (
                  <>
                    <span>Confirm Plan</span>
                    <Check size={14} />
                  </>
              )}
          </button>
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
