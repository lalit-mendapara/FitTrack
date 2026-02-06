
import { useState, useEffect, useRef, useCallback } from 'react';
import { getProfile } from '../services/profileService';
import { getDoWorkoutPreferencesExist, getCurrentWorkoutPlan } from '../services/workoutService';
import { getCurrentMealPlan } from '../services/mealPlanService';
import { useAuth } from '../context/AuthContext';

/**
 * useProfile Hook
 * Manages the state of User Profile existence (Physical & Workout Prefs).
 * Used primarily by Dashboard to determine what to show.
 */
export const useProfile = () => {
    const { user } = useAuth();
    const [hasPhysicalProfile, setHasPhysicalProfile] = useState(null); // null = loading
    const [hasWorkoutPreferences, setHasWorkoutPreferences] = useState(null);
    const [hasDietPlan, setHasDietPlan] = useState(null);
    const [hasWorkoutPlan, setHasWorkoutPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    
    const checkPerformed = useRef(false);

    const checkStatus = useCallback(async (force = false) => {
        if (!user?.id) return;
        if (checkPerformed.current && !force) return;
        
        checkPerformed.current = true;
        setLoading(true);

        try {
            // Check Physical Profile
            try {
                await getProfile();
                setHasPhysicalProfile(true);
            } catch (err) {
                if (err.response?.status === 404) {
                    setHasPhysicalProfile(false);
                } else {
                    console.error("Profile check failed", err);
                }
            }

            // Check Workout Preferences
            try {
                const prefsExist = await getDoWorkoutPreferencesExist();
                setHasWorkoutPreferences(prefsExist);
            } catch (err) {
                 // Already handled in service, but safety catch
                 setHasWorkoutPreferences(false);
            }

            // Check Diet Plan
            if (hasPhysicalProfile !== false) { // Optimization: Don't check if profile doesn't exist
                try {
                    await getCurrentMealPlan();
                    setHasDietPlan(true);
                } catch (err) {
                    setHasDietPlan(false);
                }
            } else {
                 setHasDietPlan(false);
            }

            // Check Workout Plan
            if (hasPhysicalProfile !== false) {
                 try {
                    await getCurrentWorkoutPlan();
                    setHasWorkoutPlan(true);
                } catch (err) {
                    setHasWorkoutPlan(false);
                }
            } else {
                setHasWorkoutPlan(false);
            }

        } finally {
            setLoading(false);
        }
    }, [user?.id, hasPhysicalProfile]);

    useEffect(() => {
        checkStatus();
    }, [checkStatus]);

    const refreshProfileStatus = () => {
        checkStatus(true);
    };

    return {
        hasPhysicalProfile,
        hasWorkoutPreferences,
        hasDietPlan,
        hasWorkoutPlan,
        loading,
        refreshProfileStatus,
        setHasPhysicalProfile,     
        setHasWorkoutPreferences,
        setHasDietPlan,
        setHasWorkoutPlan
    };
};
