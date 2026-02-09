import React, { useState, useEffect } from 'react';
import { Apple, Clock, Flame, Loader2, ChevronDown, ChevronRight, Calendar, ChevronLeft } from 'lucide-react';
import { getDailyDietLogs } from '../../api/tracking';

const TodayDietLog = ({ onDataLoaded }) => {
    const [meals, setMeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isExpanded, setIsExpanded] = useState(true);
    
    // Date Selection State
    const getTodayStr = () => new Date().toISOString().split('T')[0];
    const [selectedDate, setSelectedDate] = useState(getTodayStr());
    const dateInputRef = React.useRef(null);

    useEffect(() => {
        // Default to collapsed on mobile (< 768px), expanded on desktop
        const handleResize = () => {
            if (window.innerWidth < 768) {
                setIsExpanded(false);
            } else {
                setIsExpanded(true);
            }
        };

        // Set initial state
        handleResize();
    }, []);

    useEffect(() => {
        const fetchDietLogs = async () => {
            try {
                setLoading(true);
                // Pass selectedDate to API
                const data = await getDailyDietLogs(selectedDate);
                setMeals(data.meals || []);
                // Pass calories target up to parent (DashboardOverview)
                if (onDataLoaded) {
                    onDataLoaded({
                        caloriesTarget: data.calories_target,
                        totalCalories: (data.meals || []).reduce((sum, m) => sum + (m.calories || 0), 0)
                    });
                }
            } catch (err) {
                console.error('Error fetching diet logs:', err);
                setError('Failed to load diet logs');
            } finally {
                setLoading(false);
            }
        };

        fetchDietLogs();
    }, [onDataLoaded, selectedDate]); // Add selectedDate dependency

    const totalCalories = meals.reduce((sum, meal) => sum + (meal.calories || 0), 0);

    // Format time from created_at timestamp
    const formatTime = (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    };

    if (loading) {
        return (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    // Generate Header Text
    const todayStr = getTodayStr();
    const isToday = selectedDate === todayStr;
    
    // Format selected date for display (e.g., "Feb 09")
    const dateDisplay = new Date(selectedDate).toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
    
    const headerTitle = isToday ? "Today's Diet Log" : `${dateDisplay} Diet Log`;
    const subTitle = isToday ? "Logged meals for today" : `Logged meals for ${dateDisplay}`;

    const handlePrevDay = (e) => {
        e.stopPropagation();
        const prev = new Date(selectedDate);
        prev.setDate(prev.getDate() - 1);
        setSelectedDate(prev.toISOString().split('T')[0]);
    };

    const handleNextDay = (e) => {
        e.stopPropagation();
        const next = new Date(selectedDate);
        next.setDate(next.getDate() + 1);
        const nextStr = next.toISOString().split('T')[0];
        if (nextStr <= todayStr) {
            setSelectedDate(nextStr);
        }
    };

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full transition-all duration-300">
            <div 
                className="flex items-center justify-between mb-5"
            >
                <div className="flex items-center gap-3">
                    <div 
                        className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl text-white shadow-lg shadow-emerald-200 cursor-pointer"
                        onClick={() => {
                            if (window.innerWidth < 768) setIsExpanded(!isExpanded);
                        }}
                    >
                        <Apple size={22} />
                    </div>
                    
                    <div className="flex items-center gap-2">
                        {/* Left Arrow */}
                        <button 
                            onClick={handlePrevDay}
                            className="p-1 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
                        >
                            <ChevronLeft size={20} />
                        </button>

                        <div className="relative group cursor-pointer" onClick={() => dateInputRef.current?.showPicker()}>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 leading-tight">
                                    {headerTitle}
                                </h3>
                                <p className="text-xs text-gray-500 font-medium">{subTitle}</p>
                            </div>
                            <input 
                                type="date"
                                ref={dateInputRef}
                                value={selectedDate}
                                max={todayStr}
                                onChange={(e) => setSelectedDate(e.target.value)}
                                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                            />
                        </div>

                        {/* Right Arrow */}
                        <button 
                            onClick={handleNextDay}
                            disabled={isToday}
                            className={`p-1 rounded-full text-gray-400 transition-colors ${isToday ? 'opacity-30 cursor-not-allowed' : 'hover:bg-gray-100 hover:text-gray-600'}`}
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>
                </div>
                
                <div className="flex items-center gap-3 sm:gap-4">
                    <div className="text-right hidden sm:block">
                        <span className="text-2xl font-black text-emerald-600">{Math.round(totalCalories)}</span>
                        <p className="text-xs text-gray-400 font-semibold">kcal logged</p>
                    </div>
                    {/* Log summary for collapsed mobile view */}
                    {!isExpanded && (
                        <div className="text-right sm:hidden">
                             <span className="text-lg font-black text-emerald-600">{Math.round(totalCalories)}</span>
                             <span className="text-xs text-emerald-600 ml-1">kcal</span>
                        </div>
                    )}
                    <div 
                        className="p-1 rounded-full hover:bg-gray-100 transition-colors md:hidden cursor-pointer"
                        onClick={() => setIsExpanded(!isExpanded)}
                    >
                        {isExpanded ? <ChevronDown size={20} className="text-gray-400" /> : <ChevronRight size={20} className="text-gray-400" />}
                    </div>
                </div>
            </div>

            {isExpanded && (
                <div className="space-y-3 animate-in slide-in-from-top-2 duration-300">
                    {/* Mobile Only: Show full total when expanded if hidden in header? 
                        Actually, keeping the header clean is nice. The desktop header shows it. 
                        Let's show it in header always for consistency, or adapting as above.
                    */}
                    <div className="flex sm:hidden justify-between items-center mb-4 pb-4 border-b border-gray-100">
                         <span className="text-sm font-medium text-gray-500">Total Calories</span>
                         <span className="text-xl font-black text-emerald-600">{Math.round(totalCalories)} <span className="text-xs font-normal text-gray-400">kcal</span></span>
                    </div>

                    {meals.map((meal) => (
                        <div 
                            key={meal.id}
                            className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-100 hover:shadow-md hover:border-emerald-100 transition-all duration-300 group"
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                                    <Apple size={20} />
                                </div>
                                <div>
                                    <h4 className="font-semibold text-gray-800">{meal.name}</h4>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                                            {meal.meal_type || 'Snack'}
                                        </span>
                                        <span className="text-xs text-gray-400 flex items-center gap-1">
                                            <Clock size={12} /> {formatTime(meal.created_at)}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 text-gray-600">
                                <Flame size={16} className="text-orange-500" />
                                <span className="font-bold">{Math.round(meal.calories || 0)}</span>
                                <span className="text-xs text-gray-400">kcal</span>
                            </div>
                        </div>
                    ))}

                    {meals.length === 0 && !error && (
                        <div className="text-center py-8 text-gray-400">
                            <Apple size={40} className="mx-auto mb-3 opacity-30" />
                            <p className="font-medium">No meals logged for {isToday ? 'today' : dateDisplay}</p>
                        </div>
                    )}

                    {error && (
                        <div className="text-center py-8 text-red-400">
                            <p className="font-medium">{error}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default TodayDietLog;
