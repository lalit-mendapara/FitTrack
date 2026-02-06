import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Clock, CheckCircle2, Dumbbell } from 'lucide-react';
import api from '../../api/axios';

const WorkoutCalendar = () => {
    const [weekOffset, setWeekOffset] = useState(0);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchCalendar = async () => {
        try {
            setLoading(true);
            const response = await api.get('/tracking/workout-calendar', {
                params: { week_offset: weekOffset }
            });
            setData(response.data);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch workout calendar", err);
            if (!data) setError("Failed to load calendar.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCalendar();
    }, [weekOffset]);

    const handlePrevWeek = () => {
        setWeekOffset((prev) => (prev > 0 ? prev - 1 : 0));
    };

    const handleNextWeek = () => {
        const maxWeeks = data?.total_weeks || 8;
        setWeekOffset((prev) => (prev < maxWeeks - 1 ? prev + 1 : prev));
    };

    const getTypeColor = (type) => {
        const colors = {
            'push': 'from-blue-500 to-indigo-600',
            'pull': 'from-indigo-500 to-purple-600',
            'legs': 'from-orange-400 to-pink-500',
            // Cardio removed as per request, fallback or specific check if needed
            'rest': 'from-gray-100 to-gray-200 text-gray-400', 
            'full body': 'from-violet-500 to-fuchsia-600',
        };
        const normalized = (type || '').toLowerCase();
        const foundKey = Object.keys(colors).find(k => normalized.includes(k));
        
        if (normalized.includes('rest')) return 'from-gray-100 to-gray-200 text-gray-400';
        
        return foundKey ? colors[foundKey] : 'from-indigo-400 to-purple-500';
    };

    if (error && !data) {
        return (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-red-100">
                 <p className="text-red-500 font-medium text-center">{error}</p>
                 <div className="flex justify-center mt-2">
                    <button onClick={fetchCalendar} className="text-sm text-indigo-600 hover:underline">Retry</button>
                 </div>
            </div>
        );
    }

    const currentWeek = data?.current_week || 1;
    const totalWeeks = data?.total_weeks || 8;
    const dateRange = data?.date_range || ""; 

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <div className="p-2 bg-indigo-50 rounded-lg">
                            <Calendar className="w-5 h-5 text-indigo-600" />
                        </div>
                        <h2 className="text-lg font-bold text-slate-800">
                            {totalWeeks}-Week Workout Calendar
                        </h2>
                    </div>
                </div>

                {/* Navigation */}
                <div className="flex items-center justify-between sm:justify-start gap-2 sm:gap-4 bg-slate-50 rounded-xl p-1.5 border border-slate-100 w-full sm:w-auto">
                    <button 
                        onClick={handlePrevWeek}
                        disabled={loading || weekOffset <= 0}
                        className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-slate-500 hover:text-indigo-600 disabled:opacity-50"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    
                    <div className="px-2 text-center flex-1 sm:flex-none sm:min-w-[140px]">
                        <span className="text-sm font-semibold text-slate-700 block">
                            Week {currentWeek} of {totalWeeks}
                        </span>
                        {dateRange && (
                            <span className="text-xs text-slate-400 font-medium block mt-0.5">
                                {dateRange}
                            </span>
                        )}
                    </div>

                    <button 
                        onClick={handleNextWeek}
                        disabled={loading || weekOffset >= totalWeeks - 1}
                        className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-slate-500 hover:text-indigo-600 disabled:opacity-50"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="overflow-x-auto pb-2 -mx-4 px-4 sm:overflow-visible sm:mx-0 sm:px-0 scrollbar-hide">
                <div className="grid grid-cols-7 gap-3 mb-6 min-w-[1050px] sm:min-w-0">
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                        <div key={day} className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                            {day}
                        </div>
                    ))}

                    {loading && !data ? (
                        Array(7).fill(0).map((_, i) => (
                            <div key={i} className="h-40 bg-slate-50 rounded-xl animate-pulse" />
                        ))
                    ) : (
                        data?.days.map((day, index) => {
                            const colorClass = getTypeColor(day.type);
                            const isRest = day.is_rest;
                            const title = day.title || day.type || "Workout";
                            
                            // Date Formatting from WorkoutDayCard style
                            const dateLabel = day.date_label || '';
                            const [month, dateNum] = dateLabel.split(' '); // "Feb 12" -> ["Feb", "12"]
                            
                            // Robust Date Comparison (String based to avoid Timezone issues)
                            const todayStr = new Date().toLocaleDateString('en-CA'); // "YYYY-MM-DD" local
                            const cardDateStr = day.date; // Assuming "YYYY-MM-DD" from backend
                            
                            const isToday = cardDateStr === todayStr;
                            const isPast = cardDateStr < todayStr;
                            
                            const isSkipped = isPast && day.remaining_exercises === day.total_exercises;
                            const hasStarted = day.remaining_exercises < day.total_exercises;
                            
                            // FIX: "Incomplete" means started but not finished.
                            // Applies to: 
                            // 1. Past days (that weren't fully skipped)
                            // 2. TODAY (if user has started logging)
                            const isIncomplete = !day.completed && hasStarted && (isPast || isToday);
                            
                            // Status Logic
                            let borderColor = "border-transparent";
                            let statusColor = "";
                            let statusText = "";
                            let statusBadgeColor = "";
                            
                            if (day.completed) {
                                borderColor = "border-4 border-emerald-400";
                                statusText = "Completed";
                                statusBadgeColor = "bg-emerald-400/20 text-emerald-100 ring-1 ring-emerald-400/50";
                            } else if (isSkipped) {
                                borderColor = "border-4 border-red-500"; // Red
                                statusText = "Skipped";
                                statusBadgeColor = "bg-red-500/20 text-red-100 ring-1 ring-red-500/50";
                            } else if (isIncomplete) {
                                borderColor = "border-4 border-amber-400"; // Yellow
                                statusText = "Incomplete";
                                statusBadgeColor = "bg-amber-400/20 text-amber-100 ring-1 ring-amber-400/50";
                            }

                            return (
                                <div 
                                    key={index}
                                    className={`
                                        relative group h-40 rounded-xl p-3 flex flex-col justify-between transition-all duration-300
                                        ${isRest ? 'bg-slate-50 border border-slate-100' : `bg-gradient-to-br ${colorClass} shadow-md shadow-indigo-500/10 hover:shadow-xl hover:shadow-indigo-500/20 hover:-translate-y-1 text-white`}
                                        ${borderColor} ${!isRest && (day.completed || isSkipped || isIncomplete) ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-50' : ''}
                                    `}
                                >
                                        <div className="flex flex-col h-full">
                                        <div className="flex justify-between items-start gap-2">
                                            <h3 className={`font-bold text-xs sm:text-sm leading-tight line-clamp-2 flex-1 min-w-0 pr-1 ${isRest ? 'text-slate-400' : 'text-white'}`} title={title}>
                                                {title}
                                            </h3>
                                            
                                            {/* Stylized Date Badge */}
                                            <div className={`
                                                flex flex-col items-center justify-center px-1.5 py-1 rounded-lg leading-none shrink-0 w-10
                                                ${isRest ? 'bg-white border border-slate-100' : 'bg-white/10 backdrop-blur-sm border border-white/20'}
                                            `}>
                                                <span className={`text-[9px] font-bold uppercase tracking-wider mb-0.5 ${isRest ? 'text-slate-400' : 'text-white/80'}`}>
                                                    {month}
                                                </span>
                                                <span className={`text-base font-black ${isRest ? 'text-slate-600' : 'text-white'}`}>
                                                    {dateNum}
                                                </span>
                                            </div>
                                        </div>

                                        {!isRest && (
                                            <div className="mt-auto flex justify-between items-end gap-1">
                                                <div className="flex flex-col gap-1 min-w-0 flex-1">
                                                    {/* Status Badge */}
                                                    {(day.completed || isSkipped || isIncomplete) && (
                                                        <div className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide backdrop-blur-sm truncate max-w-full ${statusBadgeColor}`}>
                                                            {statusText}
                                                        </div>
                                                    )}
                                                    
                                                    {/* Duration Display */}
                                                    <div className="flex items-center gap-1">
                                                        <Clock className="w-3 h-3 text-white/80 shrink-0" />
                                                        <span className={`text-[10px] font-bold truncate ${day.is_actual_duration && day.completed ? 'text-emerald-100' : 'text-white/80'}`}>
                                                            {day.duration}m
                                                        </span>
                                                        {day.completed && day.is_actual_duration && (
                                                             <CheckCircle2 className="w-3 h-3 text-emerald-300 shrink-0" />
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Dumbbell Icon */}
                                                {!day.completed && !isSkipped && !isIncomplete && (
                                                    <div className="text-white/90 shrink-0"> 
                                                        <Dumbbell className="w-3 h-3 opacity-50" />
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        
                                        {isRest && (
                                             <div className="mt-auto flex items-center gap-1.5 text-slate-400">
                                                 <Clock className="w-3 h-3" />
                                                 <span className="text-[10px] font-medium">Recover</span>
                                             </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
};

export default WorkoutCalendar;
