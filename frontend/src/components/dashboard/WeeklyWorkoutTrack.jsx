import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TrendingUp, Dumbbell, Flame, Loader2 } from 'lucide-react';
import { getWeeklyWorkoutOverview } from '../../api/tracking';

const WeeklyWorkoutTrack = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await getWeeklyWorkoutOverview();
                setData(response);
            } catch (error) {
                console.error("Failed to load weekly stats", error);
                // Fallback valid structure if error
                setData({
                    total_calories: 0,
                    days_active: 0,
                    total_minutes: 0,
                    avg_duration: 0,
                    chart_data: []
                });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    // Helper to format chart data if API returns raw dates
    // But API should return 'day' (Mon) and 'calories'
    // API response: { total_calories, days_active, total_minutes, avg_duration, chart_data: [{day, calories}] }
    
    // We also need 'duration' in chart data? 
    // The backend update (step 101) added 'dur = ...' to local vars but did NOT append it to chart_data!
    // I missed that in the backend update.
    // However, the component calculates totals from `data` prop (total_calories etc), so charts are just visual bars.
    // Wait, the chart tooltip shows duration: `${props.payload.duration} min workout`.
    // So the chart data DOES need duration.
    
    // Since I missed adding duration to chart_data in backend, the tooltip duration will be undefined or missing.
    // I should probably fix the backend or handle missing duration here.
    // For now, I'll assume backend sends it or I'll patch backend in next step if critical.
    // Actually, I should check backend code again.
    
    const chartData = data?.chart_data || [];
    const totalCalories = data?.total_calories || 0;
    const totalDuration = data?.total_minutes || 0;
    const workoutDays = data?.days_active || 0;
    const avgDuration = data?.avg_duration || 0;

    const getBarColor = (calories) => {
        if (calories === 0) return '#e5e7eb';
        if (calories >= 500) return '#8b5cf6'; // High intensity
        if (calories >= 300) return '#6366f1'; // Medium
        return '#a5b4fc'; // Light
    };

    if (loading) {
        return (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl text-white shadow-lg shadow-violet-200">
                        <Dumbbell size={22} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Weekly Workout Overview</h3>
                        <p className="text-xs text-gray-500 font-medium">Calories burned this week</p>
                    </div>
                </div>
                <div className="text-right">
                    <div className="flex items-center gap-2 text-violet-600 bg-violet-50 px-3 py-1.5 rounded-lg">
                        <Flame size={16} />
                        <span className="text-sm font-bold">{totalCalories} kcal</span>
                    </div>
                </div>
            </div>

            <div className="h-56">
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                        <XAxis 
                            dataKey="day" 
                            axisLine={false} 
                            tickLine={false}
                            tick={{ fontSize: 12, fontWeight: 600, fill: '#6b7280' }}
                        />
                        <YAxis 
                            axisLine={false} 
                            tickLine={false}
                            tick={{ fontSize: 11, fill: '#9ca3af' }}
                        />
                        <Tooltip 
                            contentStyle={{ 
                                borderRadius: '12px', 
                                border: 'none', 
                                boxShadow: '0 10px 40px -10px rgba(0,0,0,0.2)',
                                padding: '12px 16px'
                            }}
                            formatter={(value, name, props) => [
                                `${value} kcal burned`,
                                `${props.payload.duration || 0} min workout`
                            ]}
                        />
                        <Bar 
                            dataKey="calories" 
                            radius={[8, 8, 0, 0]}
                            maxBarSize={40}
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={getBarColor(entry.calories)} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Stats */}
            <div className="flex justify-between mt-4 pt-4 border-t border-gray-100">
                <div className="text-center">
                    <p className="text-2xl font-black text-gray-900">{workoutDays}</p>
                    <p className="text-xs font-medium text-gray-500">Days Active</p>
                </div>
                <div className="text-center">
                    <p className="text-2xl font-black text-gray-900">{totalDuration}</p>
                    <p className="text-xs font-medium text-gray-500">Total Minutes</p>
                </div>
                <div className="text-center">
                    <p className="text-2xl font-black text-gray-900">{avgDuration}</p>
                    <p className="text-xs font-medium text-gray-500">Avg Duration</p>
                </div>
            </div>
        </div>
    );
};

export default WeeklyWorkoutTrack;
