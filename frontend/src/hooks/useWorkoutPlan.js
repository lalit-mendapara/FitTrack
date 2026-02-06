
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { getCurrentWorkoutPlan, generateWorkoutPlan, getWorkoutPreferences } from '../services/workoutService';
import { getProfile } from '../services/profileService';

export const useWorkoutPlan = (onGenerateStart, onGenerateEnd) => {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [showProfileUpdateWarning, setShowProfileUpdateWarning] = useState(false);

    const fetchPlan = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // 1. Fetch Plan
            let planData = null;
            try {
                planData = await getCurrentWorkoutPlan();
                setPlan(planData);
            } catch (err) {
                if (err.response?.status === 404) {
                     setPlan(null);
                } else {
                     console.error("Error fetching workout plan", err);
                     setError("Failed to load workout plan");
                }
            }

            // 2. Check Timestamps for Warning
            if (planData) {
                const planTime = new Date(planData.updated_at || planData.created_at).getTime();
                let latestProfileChange = 0;

                try {
                    const profile = await getProfile();
                    if (profile?.last_physical_update) {
                         latestProfileChange = Math.max(latestProfileChange, new Date(profile.last_physical_update).getTime());
                    } else if (profile?.updated_at) {
                         // Fallback for old records or if field missing
                         latestProfileChange = Math.max(latestProfileChange, new Date(profile.updated_at).getTime());
                    }
                } catch (e) {}

                try {
                    const prefs = await getWorkoutPreferences();
                    if (prefs?.updated_at) {
                        latestProfileChange = Math.max(latestProfileChange, new Date(prefs.updated_at).getTime());
                    }
                } catch (e) {}
                
                if (latestProfileChange > planTime + 5000) {
                    setShowProfileUpdateWarning(true);
                } else {
                    setShowProfileUpdateWarning(false);
                }
            }

        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPlan();
    }, [fetchPlan]);

    const handleGenerate = async (customPrompt = null, options = {}) => {
        setGenerating(true);
        if (onGenerateStart) onGenerateStart();
        try {
            // Fetch prefs first as they are required for generation logic
            const prefs = await getWorkoutPreferences();
            
            await generateWorkoutPlan(prefs, customPrompt, options);
            toast.success("Workout plan generated successfully!");
            setShowProfileUpdateWarning(false); // Reset warning immediately after regeneration
            await fetchPlan();
            
        } catch (err) {
             console.error("Workout generation failed", err);
             const msg = err.response?.data?.detail || "Failed to generate plan.";
             toast.error(msg);
        } finally {
            setGenerating(false);
            if (onGenerateEnd) onGenerateEnd();
        }
    };

    return {
        plan,
        loading,
        generating,
        error,
        showProfileUpdateWarning,
        handleGenerate,
        refreshPlan: fetchPlan
    };
};
