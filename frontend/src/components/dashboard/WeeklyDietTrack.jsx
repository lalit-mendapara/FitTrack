import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../../api/axios';
import { Utensils, TrendingUp } from 'lucide-react';

const WeeklyDietTrack = () => {
    const [weeklyData, setWeeklyData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchWeeklyData = async () => {
            try {
                const response = await api.get('/tracking/weekly-diet');
                setWeeklyData(response.data);
            } catch (error) {
                console.error("Failed to fetch weekly diet data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchWeeklyData();
    }, []);

    const avgCalories = weeklyData.length > 0 
        ? Math.round(weeklyData.filter(d => d.calories > 0).reduce((sum, d) => sum + d.calories, 0) / (weeklyData.filter(d => d.calories > 0).length || 1)) 
        : 0;

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-white p-3 border border-gray-100 shadow-[0_10px_40px_-10px_rgba(0,0,0,0.2)] rounded-xl z-50">
                    <p className="text-sm font-bold text-gray-900 mb-2">{`${data.day}, ${data.date}`}</p>
                    
                    <div className="space-y-1 mb-2">
                        {data.calories_breakfast > 0 && <div className="flex justify-between text-xs items-center gap-4"><span className="text-gray-500">Breakfast</span><span className="font-semibold text-emerald-600">{data.calories_breakfast}</span></div>}
                        {data.calories_lunch > 0 && <div className="flex justify-between text-xs items-center gap-4"><span className="text-gray-500">Lunch</span><span className="font-semibold text-sky-600">{data.calories_lunch}</span></div>}
                        {data.calories_dinner > 0 && <div className="flex justify-between text-xs items-center gap-4"><span className="text-gray-500">Dinner</span><span className="font-semibold text-violet-600">{data.calories_dinner}</span></div>}
                        {data.calories_snack > 0 && <div className="flex justify-between text-xs items-center gap-4"><span className="text-gray-500">Snacks</span><span className="font-semibold text-amber-500">{data.calories_snack}</span></div>}
                        {data.calories_other > 0 && <div className="flex justify-between text-xs items-center gap-4"><span className="text-gray-500">Other</span><span className="font-semibold text-gray-400">{data.calories_other}</span></div>}
                    </div>

                    <div className="pt-2 border-t border-gray-100 flex justify-between items-center text-xs">
                        <span className="font-bold text-gray-700">Total</span>
                        <span className="font-bold text-gray-900">{data.calories} kcal</span>
                    </div>
                    <p className="text-[10px] text-gray-400 mt-1 text-right">Target: {data.target}</p>
                </div>
            );
        }
        return null;
    };

    if (loading) {
        return (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full animate-pulse">
                <div className="h-6 w-1/3 bg-gray-200 rounded mb-4"></div>
                <div className="h-48 bg-gray-100 rounded-lg"></div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-teal-500 to-emerald-600 rounded-xl text-white shadow-lg shadow-teal-200">
                        <Utensils size={22} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Weekly Diet Overview</h3>
                        <p className="text-xs text-gray-500 font-medium">Daily calorie intake this week</p>
                    </div>
                </div>
                <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg">
                    <TrendingUp size={16} />
                    <span className="text-sm font-bold">{avgCalories} avg</span>
                </div>
            </div>

            <div className="h-56">
                <ResponsiveContainer width="100%" height="100%" minWidth={0} debounce={200}>
                    <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                            domain={[0, 3000]}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f9fafb' }} />
                        <Bar dataKey="calories_breakfast" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} maxBarSize={40} />
                        <Bar dataKey="calories_lunch" stackId="a" fill="#0ea5e9" radius={[0, 0, 0, 0]} maxBarSize={40} />
                        <Bar dataKey="calories_dinner" stackId="a" fill="#8b5cf6" radius={[0, 0, 0, 0]} maxBarSize={40} />
                        <Bar dataKey="calories_snack" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} maxBarSize={40} />
                        <Bar dataKey="calories_other" stackId="a" fill="#9ca3af" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex justify-center gap-4 mt-4 pt-4 border-t border-gray-100 flex-wrap">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                    <span className="text-xs font-medium text-gray-500">Breakfast</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-sky-500"></div>
                    <span className="text-xs font-medium text-gray-500">Lunch</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-violet-500"></div>
                    <span className="text-xs font-medium text-gray-500">Dinner</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                    <span className="text-xs font-medium text-gray-500">Snacks</span>
                </div>
            </div>
        </div>
    );
};

export default WeeklyDietTrack;

