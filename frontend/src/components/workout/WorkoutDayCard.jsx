import React from 'react';
import { Calendar, MonitorPlay, Timer, Dumbbell, ChevronRight, Zap } from 'lucide-react';

const WorkoutDayCard = ({ dayPlan, onSeeExercises, date }) => {
  // Calculate Total Daily Burn
  const strengthBurn = dayPlan.exercises?.reduce((acc, curr) => acc + (curr.calories_burned || 0), 0) || 0;
  const cardioBurn = dayPlan.cardio_exercises?.reduce((acc, curr) => acc + (curr.calories_burned || 0), 0) || 0;
  const totalDailyBurn = Math.round(strengthBurn + cardioBurn);
  
  // Format Date
  const dateObj = date ? new Date(date) : null;
  const dateDisplay = dateObj ? dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }) : '';
  const isToday = dateObj && new Date().toDateString() === dateObj.toDateString();

  return (
    <div className={`bg-white rounded-[2rem] shadow-xl border overflow-hidden hover:shadow-2xl transition-all duration-300 group relative ${isToday ? 'border-indigo-200 ring-2 ring-indigo-100' : 'border-gray-100/50'}`}>
      <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
        <Dumbbell size={150} className="transform rotate-12" />
      </div>

      <div className="p-8 relative z-10 flex flex-col h-full">
        <div className="flex flex-col gap-4 mb-6">
            <div className="flex items-start justify-between">
                 <div className="flex items-center gap-3">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex flex-col items-center justify-center text-white shadow-lg shadow-indigo-200 shrink-0">
                        {/* Display Date Day */}
                        <span className="text-xs font-medium opacity-80 uppercase tracking-widest">{dayPlan.day_name.substring(0, 3)}</span>
                        <span className="text-2xl font-black leading-none">{dateDisplay.split(' ')[1]}</span>
                    </div>
                </div>
                {/* Stats Badge */}
                <div className="flex gap-2 self-start">
                     {/* Time Badge */}
                    <div className="px-3 py-1 bg-indigo-50 rounded-lg flex items-center gap-1.5 border border-indigo-100/50">
                        <Timer size={14} className="text-indigo-600" />
                        <span className="text-xs font-bold text-gray-700">{dayPlan.session_duration_min} Min</span>
                    </div>
                    {/* Calorie Badge */}
                    {totalDailyBurn > 0 && (
                        <div className="px-3 py-1 bg-red-50 rounded-lg flex items-center gap-1.5 border border-red-100/50">
                            <Zap size={14} className="text-red-500 fill-current" />
                            <span className="text-xs font-bold text-gray-700">{totalDailyBurn} Kcal</span>
                        </div>
                    )}
                </div>
            </div>
            
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <h2 className="text-2xl font-black text-gray-900 tracking-tight leading-tight">{dayPlan.day_name}</h2>
                     {isToday && (
                        <span className="px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-wide rounded-full">
                            Today
                        </span>
                    )}
                </div>
                <h3 className="text-base font-bold text-indigo-600 line-clamp-2 leading-snug">{dayPlan.workout_name || dayPlan.focus}</h3>
            </div>
        </div>

        <div className="bg-gray-50/80 rounded-2xl p-5 border border-gray-100 mb-8 backdrop-blur-sm flex-1">
            <h4 className="text-[10px] font-extrabold text-gray-400 uppercase tracking-widest mb-2">Primary Muscle Group</h4>
            <p className="text-gray-600 text-sm leading-relaxed font-medium line-clamp-4">
                {dayPlan.primary_muscle_group || dayPlan.focus}
            </p>
        </div>

        <div className="flex items-center justify-between border-t border-gray-100 pt-6 mt-auto">
            <div className="flex items-center gap-2 text-gray-500 font-medium text-sm">
                <MonitorPlay size={18} className="text-indigo-500" />
                <span>{dayPlan.exercises ? dayPlan.exercises.length : 0} Exercises</span>
            </div>
            
            <button 
                onClick={onSeeExercises}
                className="flex items-center gap-1.5 px-5 py-2.5 bg-gray-900 text-white font-bold text-sm rounded-xl hover:bg-indigo-600 transition-all transform hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-200"
            >
                Start <ChevronRight size={16} />
            </button>
        </div>
      </div>
    </div>
  );
};

export default WorkoutDayCard;
