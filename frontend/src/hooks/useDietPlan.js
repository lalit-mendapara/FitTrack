
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { getCurrentMealPlan, generateMealPlan } from '../services/mealPlanService';
import { getProfile } from '../services/profileService';

export const useDietPlan = (onGenerateStart, onGenerateEnd) => {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [showProfileUpdateWarning, setShowProfileUpdateWarning] = useState(false);

    const fetchPlan = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // 1. Check Profile (for timestamp comparison)
            let currentProfile = null;
            try {
                currentProfile = await getProfile();
            } catch (err) {
                if (err.response?.status === 404) {
                    setError("PROFILE_MISSING");
                    return;
                }
            }

            // 2. Get Plan
            try {
                const planData = await getCurrentMealPlan();
                setPlan(planData);

                // 3. Compare Timestamps
                if (currentProfile && planData?.created_at) {
                    // Use last_physical_update (if available) to avoid false warnings from internal updates
                    // Fallback to updated_at only if last_physical_update is missing (legacy data)
                    const profileTimestamp = currentProfile.last_physical_update || currentProfile.updated_at;
                    
                    const profileTime = new Date(profileTimestamp).getTime();
                    const planTime = new Date(planData.created_at).getTime();
                    
                    if (profileTime > planTime + 5000) {
                        setShowProfileUpdateWarning(true);
                    } else {
                        setShowProfileUpdateWarning(false);
                    }
                }
            } catch (err) {
                if (err.response?.status === 404) {
                    setPlan(null);
                } else {
                    console.error("Error fetching plan:", err);
                    setError("Failed to load diet plan.");
                }
            }

        } catch (err) {
            console.error(err);
            setError("Something went wrong.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPlan();
    }, [fetchPlan]);

    const handleGenerate = async (customPrompt = null) => {
        setGenerating(true);
        if (onGenerateStart) onGenerateStart();
        
        try {
            await generateMealPlan(customPrompt);
            toast.success("Meal plan generated successfully!");
            setShowProfileUpdateWarning(false); // Reset warning immediately after regeneration
            await fetchPlan(); // Refresh
        } catch (err) {
            console.error("Generation failed", err);
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
