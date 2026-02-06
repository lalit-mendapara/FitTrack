import React, { useEffect, useState } from 'react';
import api from '../../api/axios';

const WeeklyGoals = ({ hasDietPlan, hasWorkoutPlan }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchGoals = async () => {
             // Only fetch if at least one plan exists to avoid unnecessary 404s/errors
             // content loaded logic handled by parent anyway
            try {
                const response = await api.get('/tracking/weekly-goals');
                setData(response.data);
            } catch (error) {
                console.error("Failed to fetch weekly goals", error);
            } finally {
                setLoading(false);
            }
        };

        if (hasDietPlan || hasWorkoutPlan) {
            fetchGoals();
        } else {
            setLoading(false);
        }
    }, [hasDietPlan, hasWorkoutPlan]);

    if (loading) return <div className="h-64 animate-pulse bg-gray-100 rounded-xl" />;
    
    // Default safe values
    const overall = data ? data.overall_percentage : 0;
    const workoutCurrent = data ? data.workout.current : 0;
    const workoutTarget = data ? data.workout.target : 0;
    const dietCurrent = data ? data.diet.current : 0;
    const dietTarget = data ? data.diet.target : 0; // Fixed typo from 'diest' if it existed, assuming 'diet' is correct key

    // Radius and circumference for SVG circle
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (overall / 100) * circumference;

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 sm:p-6 flex flex-col justify-center items-center h-full">
            <div className={`relative w-32 h-32 mb-4 flex items-center justify-center transition-opacity duration-300 ${!hasDietPlan && !hasWorkoutPlan ? 'opacity-50 grayscale' : ''}`}>
                {/* Background Circle */}
                <svg className="transform -rotate-90 w-32 h-32">
                    <circle
                        cx="64"
                        cy="64"
                        r={radius}
                        stroke="#EDE9FE" // Light purple background
                        strokeWidth="12"
                        fill="transparent"
                    />
                    {/* Progress Circle */}
                    <circle
                        cx="64"
                        cy="64"
                        r={radius}
                        stroke="#8B5CF6" // Purple
                        strokeWidth="12"
                        fill="transparent"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl font-black text-indigo-600">{overall}%</span>
                </div>
            </div>

            <div className="text-center">
                <h3 className="text-lg font-bold text-gray-900 mb-1">Weekly Goals</h3>
                <p className="text-sm text-gray-500 mb-4">You're crushing it! Keep going.</p>
                
                <div className="flex justify-center gap-4 sm:gap-8">
                    <div className={`text-center transition-all duration-300 ${!hasWorkoutPlan ? 'opacity-30 blur-[1px]' : ''}`}>
                        <p className="text-xl font-black text-emerald-600">
                            {workoutCurrent}/{workoutTarget}
                        </p>
                        <p className="text-xs text-gray-500 font-medium">Workouts</p>
                    </div>
                    <div className={`text-center transition-all duration-300 ${!hasDietPlan ? 'opacity-30 blur-[1px]' : ''}`}>
                        <p className="text-xl font-black text-indigo-600">
                             {dietCurrent}/{dietTarget}
                        </p>
                        <p className="text-xs text-gray-500 font-medium">Diet Days</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WeeklyGoals;
