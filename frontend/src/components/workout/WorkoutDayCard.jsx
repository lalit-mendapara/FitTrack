import React from 'react';
import { Calendar, MonitorPlay, Timer, Dumbbell, ChevronRight, Zap } from 'lucide-react';

const WorkoutDayCard = ({ dayPlan, onSeeExercises, date, feastStatus }) => {
  // Feast Mode Detection
  const isFeastDate = feastStatus?.event_date === date;
  const isFeastMode = dayPlan.workout_split?.toLowerCase().includes('feast') || dayPlan.workout_name?.toLowerCase().includes('feast') || isFeastDate;

  // Compute Effective Day Plan (Inject Feast Workout Data if applicable)
  const effectiveDayPlan = isFeastDate && feastStatus?.feast_workout_data
    ? {
        ...dayPlan,
        workout_name: feastStatus.feast_workout_data.workout_name || (feastStatus.event_name ? `Feast Day: ${feastStatus.event_name}` : "Feast Mode Workout"),
        primary_muscle_group: feastStatus.feast_workout_data.primary_muscle_group || "Full Body",
        focus: feastStatus.feast_workout_data.focus || "Glycogen Depletion",
        exercises: feastStatus.feast_workout_data.exercises || [],
        cardio_exercises: feastStatus.feast_workout_data.cardio_exercises || [],
        session_duration_min: feastStatus.feast_workout_data.session_duration_min || dayPlan.session_duration_min
      }
    : dayPlan;

  // Calculate Total Daily Burn
  const strengthBurn = effectiveDayPlan.exercises?.reduce((acc, curr) => acc + (curr.calories_burned || 0), 0) || 0;
  const cardioBurn = effectiveDayPlan.cardio_exercises?.reduce((acc, curr) => acc + (curr.calories_burned || 0), 0) || 0;
  const totalDailyBurn = Math.round(strengthBurn + cardioBurn);
  
  // Format Date
  const dateObj = date ? new Date(date) : null;
  const dateDisplay = dateObj ? dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }) : '';
  const isToday = dateObj && new Date().toDateString() === dateObj.toDateString();


  return (
    <div className={`bg-white rounded-4xl shadow-xl border overflow-hidden hover:shadow-2xl transition-all duration-300 group relative 
        ${isFeastMode ? 'border-purple-200 ring-2 ring-purple-100 shadow-purple-100' : isToday ? 'border-indigo-200 ring-2 ring-indigo-100' : 'border-gray-100/50'}`}>
      <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
        <Dumbbell size={150} className={`transform rotate-12 ${isFeastMode ? 'text-purple-500' : ''}`} />
      </div>

      <div className="p-8 relative z-10 flex flex-col h-full">
        <div className="flex flex-col gap-4 mb-6">
            <div className="flex items-start justify-between gap-3">
                 <div className="flex items-center gap-3">
                    <div className={`w-14 h-14 sm:w-16 sm:h-16 rounded-2xl flex flex-col items-center justify-center text-white shadow-lg shrink-0
                        ${isFeastMode ? 'bg-linear-to-br from-purple-500 to-indigo-600 shadow-purple-200' : 'bg-linear-to-br from-indigo-500 to-purple-600 shadow-indigo-200'}`}>
                        {/* Display Date Day */}
                        <span className="text-[10px] sm:text-xs font-medium opacity-80 uppercase tracking-widest">{effectiveDayPlan.day_name.substring(0, 3)}</span>
                        <span className="text-xl sm:text-2xl font-black leading-none">{dateDisplay.split(' ')[1]}</span>
                    </div>
                </div>
                {/* Stats Badge */}
                <div className="flex gap-1.5 sm:gap-2 self-start flex-col items-end">
                     {/* Feast Badge */}
                     {isFeastMode && (
                         <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold uppercase tracking-wide rounded-full border border-purple-200">
                             Feast Mode
                         </span>
                     )}
                     <div className="flex flex-wrap justify-end gap-1.5 sm:gap-2">
                        {/* Time Badge */}
                        <div className="px-2 py-0.5 sm:px-3 sm:py-1 bg-indigo-50 rounded-lg flex items-center gap-1 sm:gap-1.5 border border-indigo-100/50">
                            <Timer size={12} className="text-indigo-600 sm:w-3.5 sm:h-3.5 w-3 h-3" />
                            <span className="text-[10px] sm:text-xs font-bold text-gray-700">{effectiveDayPlan.session_duration_min} Min</span>
                        </div>
                        {/* Calorie Badge */}
                        {totalDailyBurn > 0 && (
                            <div className={`px-2 py-0.5 sm:px-3 sm:py-1 rounded-lg flex items-center gap-1 sm:gap-1.5 border ${isFeastMode ? 'bg-purple-50 border-purple-100/50' : 'bg-red-50 border-red-100/50'}`}>
                                <Zap size={12} className={`fill-current sm:w-3.5 sm:h-3.5 w-3 h-3 ${isFeastMode ? 'text-purple-500' : 'text-red-500'}`} />
                                <span className="text-[10px] sm:text-xs font-bold text-gray-700">{totalDailyBurn} Kcal</span>
                            </div>
                        )}
                     </div>
                </div>
            </div>
            
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <h2 className="text-2xl font-black text-gray-900 tracking-tight leading-tight">{effectiveDayPlan.day_name}</h2>
                     {isToday && (
                        <span className="px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-wide rounded-full">
                            Today
                        </span>
                    )}
                </div>
                <h3 className={`text-base font-bold line-clamp-2 leading-snug ${isFeastMode ? 'text-purple-600' : 'text-indigo-600'}`}>
                    {effectiveDayPlan.workout_name || effectiveDayPlan.focus}
                </h3>
            </div>
        </div>

        <div className="bg-gray-50/80 rounded-2xl p-5 border border-gray-100 mb-8 backdrop-blur-sm flex-1">
            <h4 className="text-[10px] font-extrabold text-gray-400 uppercase tracking-widest mb-2">Primary Muscle Group</h4>
            <p className="text-gray-600 text-sm leading-relaxed font-medium line-clamp-4">
                {effectiveDayPlan.primary_muscle_group || effectiveDayPlan.focus}
            </p>
        </div>

        <div className="flex items-center justify-between border-t border-gray-100 pt-6 mt-auto">
            <div className="flex items-center gap-2 text-gray-500 font-medium text-sm">
                <MonitorPlay size={18} className="text-indigo-500" />
                <span>{(effectiveDayPlan.exercises?.length || 0) + (effectiveDayPlan.cardio_exercises?.length || 0)} Exercises</span>
            </div>
            
            <button 
                onClick={onSeeExercises}
                className={`flex items-center gap-1.5 px-5 py-2.5 text-white font-bold text-sm rounded-xl transition-all transform hover:-translate-y-0.5 hover:shadow-lg
                    ${isFeastMode ? 'bg-purple-900 hover:bg-purple-600 hover:shadow-purple-200' : 'bg-gray-900 hover:bg-indigo-600 hover:shadow-indigo-200'}`}
            >
                Start <ChevronRight size={16} />
            </button>
        </div>
      </div>
    </div>
  );
};

export default WorkoutDayCard;
