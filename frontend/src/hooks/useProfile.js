
import { useState, useEffect, useRef, useCallback } from 'react';
import { getProfile } from '../services/profileService';
import { getDoWorkoutPreferencesExist } from '../services/workoutService';
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

        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    useEffect(() => {
        checkStatus();
    }, [checkStatus]);

    const refreshProfileStatus = () => {
        checkStatus(true);
    };

    return {
        hasPhysicalProfile,
        hasWorkoutPreferences,
        loading,
        refreshProfileStatus,
        setHasPhysicalProfile,     // expose setters for optimistic updates
        setHasWorkoutPreferences
    };
};
