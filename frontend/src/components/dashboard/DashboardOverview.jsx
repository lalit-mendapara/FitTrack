import React, { useState, useCallback, useEffect } from 'react';
import TodayDietLog from './TodayDietLog';
import TodayWorkoutLog from './TodayWorkoutLog';

import WeeklyDietTrack from './WeeklyDietTrack';
import WeeklyWorkoutOverview from './WeeklyWorkoutOverview.jsx';
import WeeklyGoals from './WeeklyGoals.jsx';
import WorkoutCalendar from './WorkoutCalendar';
import { LayoutDashboard, Sparkles, Target, Flame, Bell, X } from 'lucide-react';
import { getUnreadNotifications, markNotificationRead } from '../../api/notifications';
import { updateTimezone } from '../../api/user_profile';
import { getActiveSocialEvent } from '../../api/socialEventService';
import LockOverlay from '../common/LockOverlay';
import FeastActivationCard from './FeastActivationCard';
import { useDietPlan } from '../../hooks/useDietPlan';
import feastModeService from '../../api/feastModeService';

const DashboardOverview = ({ hasDietPlan, hasWorkoutPlan }) => {
    const [dietData, setDietData] = useState({ caloriesTarget: 0, totalCalories: 0 });
    const [workoutData, setWorkoutData] = useState({ totalCalories: 0 });
    const [notifications, setNotifications] = useState([]);
    const [showNotifications, setShowNotifications] = useState(true);
    const [feastStatus, setFeastStatus] = useState(null);
    const { plan } = useDietPlan();
    
    // Lifted State for Week Offset (Synchronizes Calendar, Overview, and Goals)
    const [weekOffset, setWeekOffset] = useState(0); 

    // Initial Setup: Timezone & Notifications
    // 3. Fetch Active Social Event (Feast Mode)
    const fetchFeastStatus = useCallback(async () => {
        try {
             const status = await feastModeService.getStatus();
             setFeastStatus(status);
        } catch (e) {
            console.error("Failed to fetch feast status", e);
        }
    }, []);

    useEffect(() => {
        // 1. Sync Timezone
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        updateTimezone(tz).catch(err => console.error("Timezone sync failed", err));

        // 2. Fetch Notifications
        const fetchNotifications = async () => {
            const data = await getUnreadNotifications();
            if (data && data.length > 0) {
                setNotifications(data);
            }
        };
        fetchNotifications();
        
        // 3. Initial Social Event Fetch
        fetchFeastStatus();
    }, [fetchFeastStatus]);

    const handleDismissNotification = async (id) => {
        await markNotificationRead(id);
        setNotifications(prev => prev.filter(n => n.id !== id));
    };

    // Callback to receive data from TodayDietLog
    const handleDietDataLoaded = useCallback((data) => {
        setDietData(data);
    }, []);

    // Callback to receive data from TodayWorkoutLog
    const handleWorkoutDataLoaded = useCallback((data) => {
        setWorkoutData(data);
    }, []);

    const baseCaloriesTarget = plan?.daily_generated_totals?.calories || dietData.caloriesTarget;

    const progressPercent = baseCaloriesTarget > 0 
        ? Math.min((dietData.totalCalories / baseCaloriesTarget) * 100, 100)
        : 0;

    return (
        <div className="space-y-6">
            {/* Feast Mode Card */}
            <FeastActivationCard onStatusChange={setFeastStatus} />

            {/* Feast Mode Banner (Legacy/Optional - removed for now to avoid duplication) */}
            {/* {feastStatus?.is_active && <FeastModeBanner event={feastStatus.config} onUpdate={fetchFeastStatus} />} */}

            {/* Notifications Banner */}
            {showNotifications && notifications.length > 0 && (
                <div className="space-y-2">
                    {notifications.map(notif => (
                        <div key={notif.id} className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-4 text-white shadow-lg flex items-center justify-between animate-in slide-in-from-top-2">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                                    <Bell size={20} className="text-white" />
                                </div>
                                <div>
                                    <p className="font-medium text-sm md:text-base">{notif.message}</p>
                                    <p className="text-xs text-indigo-100 opacity-90">Just now</p>
                                </div>
                            </div>
                            <button 
                                onClick={() => handleDismissNotification(notif.id)}
                                className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                            >
                                <X size={18} />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Header */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 md:p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl text-white shadow-lg shadow-indigo-200">
                            <LayoutDashboard size={28} />
                        </div>
                        <div>
                            <h1 className="text-2xl font-black text-gray-900 flex items-center gap-2">
                                Dashboard Overview
                                <Sparkles size={20} className="text-amber-500" />
                            </h1>
                            <p className="text-sm text-gray-500 font-medium">Your fitness journey at a glance</p>
                        </div>
                    </div>
                    
                    {/* Calories Target - Right side */}
                    {baseCaloriesTarget > 0 && (
                        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
                            {/* Workout To Burn */}
                            <div className="flex flex-1 items-center justify-between sm:justify-start gap-4 bg-gradient-to-r from-orange-50 to-red-50 px-5 py-3 rounded-xl border border-orange-100">
                                <div className="flex items-center gap-2">
                                    <Flame size={20} className="text-orange-600" />
                                    <span className="text-sm font-medium text-gray-600">To Burn</span>
                                </div>
                                <div className="text-right">
                                    <div className="flex items-baseline gap-1">
                                        <span className="text-2xl font-black text-orange-600">
                                            {workoutData.remainingCalories || 0}
                                        </span>
                                        <span className="text-xs text-gray-400 font-medium">/ {Math.round(workoutData.targetCalories || 0)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Remaining Calories */}
                            <div className="flex flex-1 items-center justify-between sm:justify-start gap-4 bg-gradient-to-r from-emerald-50 to-teal-50 px-5 py-3 rounded-xl border border-emerald-100">
                                <div className="flex items-center gap-2">
                                    <Target size={20} className="text-emerald-600" />
                                    <span className="text-sm font-medium text-gray-600">Remaining</span>
                                </div>
                                <div className="text-right">
                                    <div className="flex items-baseline gap-1">
                                        <span className="text-2xl font-black text-emerald-600">
                                            {Math.max(0, Math.round(baseCaloriesTarget - dietData.totalCalories))}
                                        </span>
                                        <span className="text-xs text-gray-400 font-medium">/ {Math.round(baseCaloriesTarget)}</span>
                                    </div>
                                    <div className="w-24 h-1.5 bg-gray-200 rounded-full mt-1 ml-auto">
                                        <div 
                                            className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                                            style={{ width: `${progressPercent}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Today's Activity - Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
                <LockOverlay 
                    isLocked={!hasDietPlan} 
                    message="Diet Plan Not Generated" 
                    actionLink="/dashboard?tab=diet-plan" 
                    actionLabel="Generate Plan"
                >
                    <TodayDietLog onDataLoaded={handleDietDataLoaded} />
                </LockOverlay>

                <LockOverlay 
                    isLocked={!hasWorkoutPlan} 
                    message="Workout Plan Not Generated" 
                    actionLink="/dashboard?tab=workout-plan"
                    actionLabel="Generate Plan"
                >
                    <TodayWorkoutLog onDataLoaded={handleWorkoutDataLoaded} />
                </LockOverlay>
            </div>

            {/* Daily Tracking - Row 2 */}
            <div className="w-full">
                <LockOverlay 
                    isLocked={!hasDietPlan} 
                    message="Diet Plan Not Generated" 
                    actionLink="/dashboard?tab=diet-plan"
                    actionLabel="Generate Plan"
                >
                    <WeeklyDietTrack />
                </LockOverlay>
            </div>

            {/* Weekly Tracking - Row 3 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
                <LockOverlay 
                    isLocked={!hasWorkoutPlan} 
                    message="Workout Plan Not Generated" 
                    actionLink="/dashboard?tab=workout-plan"
                    actionLabel="Generate Plan"
                >
                    <WeeklyWorkoutOverview weekOffset={weekOffset} />
                </LockOverlay>
                <WeeklyGoals hasDietPlan={hasDietPlan} hasWorkoutPlan={hasWorkoutPlan} weekOffset={weekOffset} />
            </div>

            {/* 8-Week Calendar - Row 4 */}
            <LockOverlay 
                isLocked={!hasWorkoutPlan} 
                message="Workout Plan Not Generated" 
                actionLink="/dashboard?tab=workout-plan"
                actionLabel="Generate Plan"
            >
                <WorkoutCalendar 
                    isLocked={!hasWorkoutPlan} 
                    currentWeekOffset={weekOffset}
                    onWeekChange={setWeekOffset}
                />
            </LockOverlay>
        </div>
    );
};

export default DashboardOverview;
