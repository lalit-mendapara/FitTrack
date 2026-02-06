import React, { useState, useEffect } from 'react';
import api from '../../api/axios';
import { toast } from 'react-toastify';

const WorkoutPreferencesForm = ({ existingData, onSuccess, onUpdateStart, onUpdateEnd }) => {
    const [formData, setFormData] = useState({
        experience_level: 'beginner',
        days_per_week: 3,
        session_duration_min: 30,
        health_restrictions: ''
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (existingData) {
            setFormData({
                experience_level: existingData.experience_level || 'beginner',
                days_per_week: existingData.days_per_week || 3,
                session_duration_min: existingData.session_duration_min || 30,
                health_restrictions: existingData.health_restrictions || ''
            });
        }
    }, [existingData]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        if (onUpdateStart) onUpdateStart(); // Trigger global loading state

        try {
            await api.post('/workout-preferences/', formData);
            toast.success("Workout preferences saved");
            if (onSuccess) onSuccess();
        } catch (error) {
            console.error("Error updating workout preferences:", error);
            toast.error("Failed to update workout preferences.");
        } finally {
            setLoading(false);
            if (onUpdateEnd) onUpdateEnd(); // Stop global loading state
        }
    };

    return (
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full h-full flex flex-col">
            <div className="mb-8 text-center">
                <h2 className="text-3xl font-bold text-gray-900">
                    {existingData ? 'Update Preferences' : 'Workout Preferences'}
                </h2>
                <p className="text-gray-500 mt-2">
                    Customize your workout plan to fit your lifestyle.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8 flex flex-col flex-1">
                
                {/* Experience Level */}
                <div className="space-y-4">
                    <label className="block text-sm font-medium text-gray-700">Experience Level</label>
                    <div className="grid grid-cols-3 gap-3">
                        {['beginner', 'intermediate', 'advanced'].map((level) => (
                            <button
                                key={level}
                                type="button"
                                onClick={() => setFormData(prev => ({ ...prev, experience_level: level }))}
                                className={`py-3 px-4 rounded-lg capitalize transition-colors border-2 font-medium ${
                                    formData.experience_level === level
                                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                                    : 'border-gray-200 hover:border-indigo-200 text-gray-600'
                                }`}
                            >
                                {level}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Days Per Week */}
                <div className="space-y-4">
                    <label className="block text-sm font-medium text-gray-700">Days Per Week</label>
                    <div className="flex items-center gap-4">
                        <input
                            type="range"
                            min="1"
                            max="7"
                            name="days_per_week"
                            value={formData.days_per_week}
                            onChange={handleChange}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                        />
                        <span className="text-2xl font-bold text-indigo-600 w-8 text-center">{formData.days_per_week}</span>
                    </div>
                     <p className="text-xs text-gray-500">How many days can you workout?</p>
                </div>

                 {/* Session Duration */}
                 <div className="space-y-4">
                    <label className="block text-sm font-medium text-gray-700">Session Duration (minutes)</label>
                    <div className="flex items-center gap-4">
                        <input
                            type="number"
                            min="10"
                            step="5"
                            name="session_duration_min"
                            value={formData.session_duration_min}
                            onChange={handleChange}
                             className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                        />
                    </div>
                </div>

                {/* Health Restrictions */}
                <div className="space-y-4">
                    <label htmlFor="health_restrictions" className="block text-sm font-medium text-gray-700">
                        Health Restrictions (Optional)
                    </label>
                    <textarea
                        id="health_restrictions"
                        name="health_restrictions"
                        rows="3"
                        value={formData.health_restrictions}
                        onChange={handleChange}
                        placeholder="Any injuries or limitations..."
                         className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-gray-50"
                    />
                </div>

                <div className="pt-6 mt-auto">
                    <button
                        type="submit"
                        disabled={loading}
                        className={`w-full py-4 px-6 border border-transparent rounded-xl shadow-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 font-bold text-lg transition-all transform hover:-translate-y-1 ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
                    >
                        {loading ? 'Saving Preferences...' : 'Update Preferences'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default WorkoutPreferencesForm;
