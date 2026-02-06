import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../../api/axios';
import { Dumbbell, Flame, Timer, CalendarDays } from 'lucide-react';

const WeeklyWorkoutOverview = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get('/tracking/weekly-workout');
        setData(response.data);
      } catch (error) {
        console.error("Failed to fetch weekly workout data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="h-64 animate-pulse bg-gray-100 rounded-xl" />;
  
  if (!data) return null;

  return (
    <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
      <div className="flex flex-col sm:flex-row justify-between items-start mb-8 gap-4 sm:gap-0">
        <div className="flex gap-4 items-center">
          <div className="p-3.5 bg-purple-600 rounded-xl text-white shadow-lg shadow-purple-200">
            <Dumbbell size={28} />
          </div>
          <div>
            <h3 className="font-bold text-lg text-gray-900 leading-tight">Weekly Workout Overview</h3>
            <p className="text-gray-500 text-sm">Calories burned this week</p>
          </div>
        </div>
        <div className="flex flex-col items-start sm:items-end w-full sm:w-auto">
            <div className="bg-purple-50 px-4 py-2 rounded-lg text-purple-700 font-bold flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-start">
            <Flame size={18} />
            {data.total_calories} <span className="text-purple-400 text-xs font-medium">/ {data.expected_calories || 0} kcal</span>
            </div>
        </div>
      </div>

      <div className="h-64 w-full mb-8">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} debounce={200}>
          <BarChart data={data.chart_data} barSize={40}>
            <XAxis 
                dataKey="day" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#9CA3AF', fontSize: 12 }} 
                dy={10}
            />
             {/* Hide Y Axis as per design, but keep grid or remove it? Design has grid lines. */}
             <YAxis hide={true} />
            <Tooltip 
                cursor={{ fill: 'transparent' }}
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                labelStyle={{ color: '#6B7280', marginBottom: '0.25rem' }}
                formatter={(value) => [`${value} kcal`]} // Hide "calories" label key if prefered, or customise
                labelFormatter={(label, payload) => {
                  if (payload && payload.length > 0) {
                    return payload[0].payload.date_label; // Show "23 Oct" instead of "Mon"
                  }
                  return label;
                }}
            />
            <Bar dataKey="calories" radius={[8, 8, 8, 8]}>
              {data.chart_data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill="#8B5CF6" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4 border-t border-gray-100 pt-6">
        <div className="text-center">
            <div className="flex justify-center mb-1 text-gray-900 font-bold text-2xl">
                {data.days_active}
            </div>
            <div className="text-xs text-gray-500 font-medium">Days Active</div>
        </div>
        <div className="text-center border-l border-gray-100 border-r">
            <div className="flex justify-center mb-1 text-gray-900 font-bold text-2xl">
                {data.total_minutes}
            </div>
            <div className="text-xs text-gray-500 font-medium">Total Minutes</div>
        </div>
        <div className="text-center">
            <div className="flex justify-center mb-1 text-gray-900 font-bold text-2xl">
                {data.avg_duration}
            </div>
            <div className="text-xs text-gray-500 font-medium">Avg Duration</div>
        </div>
      </div>
    </div>
  );
};

export default WeeklyWorkoutOverview;
