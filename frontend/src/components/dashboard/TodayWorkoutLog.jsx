import React, { useState, useEffect } from 'react';
import { Dumbbell, Clock, Flame, Zap, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { getDailyWorkoutLogs } from '../../api/tracking';
import { debounce } from '../../utils/debounce';

const TodayWorkoutLog = ({ onDataLoaded }) => {
    const [workouts, setWorkouts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isExpanded, setIsExpanded] = useState(true);

    useEffect(() => {
        const handleResize = debounce(() => {
            if (window.innerWidth < 768) {
                setIsExpanded(false);
            } else {
                setIsExpanded(true);
            }
        }, 200);

        // Initial check
        if (window.innerWidth < 768) {
            setIsExpanded(false);
        } else {
            setIsExpanded(true);
        }

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        const fetchWorkoutLogs = async () => {
            try {
                setLoading(true);
                const data = await getDailyWorkoutLogs();
                setWorkouts(data.workouts || []);
                const targetCals = data.target_calories || 0;
                
                // Calculate total calories and pass to parent
                const totalCals = (data.workouts || []).reduce((sum, w) => sum + (w.calories || 0), 0);
                
                if (onDataLoaded) {
                    onDataLoaded({ 
                        totalCalories: totalCals,
                        targetCalories: targetCals,
                        remainingCalories: Math.max(0, targetCals - totalCals)
                    });
                }
            } catch (err) {
                console.error('Error fetching workout logs:', err);
                setError('Failed to load workout logs');
            } finally {
                setLoading(false);
            }
        };

        fetchWorkoutLogs();
    }, [onDataLoaded]);

    const totalCalories = workouts.reduce((sum, workout) => sum + (workout.calories || 0), 0);
    
    // Format time from created_at timestamp
    const formatTime = (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    };

    if (loading) {
        return (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full transition-all duration-300">
            <div 
                className="flex items-center justify-between mb-5 md:cursor-default cursor-pointer"
                onClick={() => {
                    if (window.innerWidth < 768) {
                        setIsExpanded(!isExpanded);
                    }
                }}
            >
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-lg shadow-indigo-200">
                        <Dumbbell size={22} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            Today's Workout Log
                        </h3>
                        <p className="text-xs text-gray-500 font-medium">Completed exercises today</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                        <span className="text-2xl font-black text-indigo-600">{Math.round(totalCalories)}</span>
                        <p className="text-xs text-gray-400 font-semibold">kcal burned</p>
                    </div>
                    {/* Log summary for collapsed mobile view */}
                    {!isExpanded && (
                        <div className="text-right sm:hidden">
                             <span className="text-lg font-black text-indigo-600">{Math.round(totalCalories)}</span>
                             <span className="text-xs text-indigo-600 ml-1">kcal</span>
                        </div>
                    )}
                    <div className="p-1 rounded-full hover:bg-gray-100 transition-colors md:hidden">
                        {isExpanded ? <ChevronDown size={20} className="text-gray-400" /> : <ChevronRight size={20} className="text-gray-400" />}
                    </div>
                </div>
            </div>

            {isExpanded && (
                <div className="space-y-3 animate-in slide-in-from-top-2 duration-300">
                     <div className="flex sm:hidden justify-between items-center mb-4 pb-4 border-b border-gray-100">
                         <span className="text-sm font-medium text-gray-500">Total Burned</span>
                         <span className="text-xl font-black text-indigo-600">{Math.round(totalCalories)} <span className="text-xs font-normal text-gray-400">kcal</span></span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {workouts.map((workout) => {
                            // Logic to distinguish: Cardio typically has duration, Strength has sets.
                            // Fallback: If duration_min exists, treat as Cardio.
                            const isCardio = (workout.duration_min && workout.duration_min > 0) || (!workout.sets && !workout.reps && workout.duration_min);
                            
                            return (
                                <div 
                                    key={workout.id}
                                    className={`flex flex-col p-3 rounded-xl border hover:shadow-md transition-all duration-300 group h-full ${
                                        isCardio 
                                        ? 'bg-orange-50/50 border-orange-200 hover:border-orange-300' 
                                        : 'bg-purple-50/50 border-purple-200 hover:border-purple-300' 
                                    }`}
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors shrink-0 ${
                                            isCardio 
                                            ? 'bg-white text-orange-600 group-hover:bg-orange-100 border border-orange-100' 
                                            : 'bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100'
                                        }`}>
                                            {workout.img_url ? (
                                                <img src={workout.img_url} alt={workout.name} className="w-full h-full object-cover rounded-xl" />
                                            ) : (
                                                <Dumbbell size={20} />
                                            )}
                                        </div>
                                        <div className={`flex items-center gap-1 font-bold text-sm px-2 py-1 rounded-lg border shadow-sm ${
                                            isCardio 
                                            ? 'bg-white text-orange-600 border-orange-100' 
                                            : 'bg-white text-indigo-600 border-indigo-100'
                                        }`}>
                                            <Flame size={14} className={isCardio ? "text-orange-500" : "text-indigo-500"} />
                                            <span>{Math.round(workout.calories || 0)}</span>
                                        </div>
                                    </div>

                                    <div className="flex-1 min-h-[3rem]">
                                        <h4 className="font-semibold text-gray-800 text-sm line-clamp-3 mb-2 leading-snug" title={workout.name}>
                                            {workout.name}
                                        </h4>
                                    </div>

                                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-black/5">
                                        <div>
                                            {workout.muscle_group && (
                                                <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded-md ${
                                                    isCardio ? 'text-orange-600 bg-orange-100/50' : 'text-indigo-600 bg-indigo-100/50'
                                                }`}>
                                                    {workout.muscle_group}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {workout.sets && (
                                                <span className={`text-[10px] font-bold flex items-center gap-0.5 ${isCardio ? 'text-orange-600' : 'text-indigo-600'}`}>
                                                    <Zap size={10} /> {workout.sets}
                                                </span>
                                            )}
                                            <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                                                <Clock size={10} /> {formatTime(workout.created_at)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {workouts.length === 0 && !error && (
                            <div className="text-center py-8 text-gray-400 col-span-full">
                                <Dumbbell size={40} className="mx-auto mb-3 opacity-30" />
                                <p className="font-medium">No workouts logged yet today</p>
                            </div>
                        )}
                        
                        {error && (
                            <div className="text-center py-8 text-red-400 col-span-full">
                                <p className="font-medium">{error}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TodayWorkoutLog;
