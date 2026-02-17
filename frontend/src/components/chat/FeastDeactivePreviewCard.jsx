import React from 'react';
import { AlertCircle, ArrowRight, Activity, Flame } from 'lucide-react';

const FeastDeactivePreviewCard = ({ preview, onConfirm, onCancel, loading }) => {
  if (!preview) return null;

  // Helper to extract meals from snapshot
  const getRestoredMeals = () => {
      if (!preview.original_diet_snapshot?.meal_plan) return [];
      const plan = preview.original_diet_snapshot.meal_plan;
      
      // If plan is an array (new format)
      if (Array.isArray(plan)) {
          return plan.map(m => {
              const n = m.nutrients || {};
              const cals = Math.round((Number(n.p||0)*4) + (Number(n.c||0)*4) + (Number(n.f||0)*9));
              return { 
                  name: m.label || m.meal_id || 'Meal', 
                  cals 
              };
          });
      }
      
      // Legacy object format
      const meals = [];
      ['breakfast', 'lunch', 'dinner', 'snack', 'snacks'].forEach(key => {
          if (plan[key]) {
              const m = plan[key];
              const n = m.nutrients || {};
              const cals = Math.round((Number(n.p||0)*4) + (Number(n.c||0)*4) + (Number(n.f||0)*9));
              meals.push({ name: key.charAt(0).toUpperCase() + key.slice(1), cals });
          }
      });
      return meals;
  };

  const restoredMeals = getRestoredMeals();

  return (
    <div className="bg-white p-5 rounded-xl border border-red-100 shadow-sm animate-in fade-in slide-in-from-bottom-2 space-y-4 max-w-sm w-full">
      <div className="flex items-center gap-3 border-b border-red-50 pb-3">
        <div className="p-2 bg-red-50 text-red-500 rounded-lg">
          <AlertCircle size={20} />
        </div>
        <div>
           <h3 className="font-bold text-gray-900">Cancel Feast Mode?</h3>
           <p className="text-xs text-gray-500">Event: {preview.event_name}</p>
        </div>
      </div>

      <div className="space-y-3 bg-gray-50 p-3 rounded-lg border border-gray-100">
         <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">Daily Calorie Target</span>
            <div className="flex items-center gap-2">
                 <span className="text-gray-400 line-through text-xs">{Math.round(preview.current_daily_calories)}</span>
                 <ArrowRight size={12} className="text-gray-400" />
                 <span className="font-bold text-gray-900">{Math.round(preview.restored_daily_calories)}</span>
            </div>
         </div>

         {preview.banked_calories_lost > 0 && (
             <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Banked Calories Lost</span>
                <span className="font-bold text-red-500">-{preview.banked_calories_lost} kcal</span>
             </div>
         )}
      </div>

      {/* Meal Breakdown */}
      {restoredMeals.length > 0 && (
          <div className="border-t border-b border-gray-100 py-2">
              <p className="text-xs font-semibold text-gray-500 mb-2">Restoring Meals:</p>
              <div className="space-y-1 max-h-32 overflow-y-auto pr-1 custom-scrollbar">
                  {restoredMeals.map((meal, idx) => (
                      <div key={idx} className="flex justify-between text-xs">
                          <span className="text-gray-700">{meal.name}</span>
                          <span className="text-gray-900 font-medium">{meal.cals} kcal</span>
                      </div>
                  ))}
              </div>
          </div>
      )}

      <div className="p-3 bg-blue-50 text-blue-800 text-xs rounded-lg border border-blue-100 flex items-start gap-2">
          <div className="mt-0.5"><Activity size={14} /></div>
          <p>{preview.workout_status}</p>
      </div>

      <div className="flex gap-2 pt-2">
           <button
             onClick={onCancel}
             className="flex-1 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors font-medium"
           >
             Keep Active
           </button>
           <button
             onClick={onConfirm}
             disabled={loading}
             className="flex-[2] py-2 text-sm bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg shadow-md transition-colors"
           >
             {loading ? 'Cancelling...' : 'Confirm Cancel'}
           </button>
      </div>
    </div>
  );
};

export default FeastDeactivePreviewCard;
