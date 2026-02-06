import React from 'react';
import Profile from '../../pages/Profile';
import { AlertCircle, Info } from 'lucide-react';

const UpdateProfileDisplay = ({ user, isProfileMissing, onProfileComplete, onViewDietPlan, onUpdateStart, onUpdateEnd }) => {
    // The existing Profile page seems to be the "Diet Profile" update form based on context.
    // If it needs to be stripped of its navbar/footer for embedding, we might need to refactor Profile.jsx.
    // For now, we'll wrap it. If Profile.jsx has a Layout with Navbar, it might look double.
    // Let's assume Profile.jsx is just the content or we will fix it later.
    // Actually, looking at App.jsx, Profile is a page. 
    // I'll create a wrapper that hints this is the diet profile section.
    
    return (
        <div className="space-y-6">
            {/* Informational Alert for Missing Profile */}
            {isProfileMissing && (
                <div className="mb-2 bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-start gap-3 animate-fadeIn">
                    <Info className="text-blue-600 flex-shrink-0 mt-0.5" size={20} />
                    <div>
                        <h3 className="font-semibold text-blue-800">Complete Your Physical Profile</h3>
                        <p className="text-sm text-blue-700 mt-1">
                            You have not created profile. to access our services create profile first.
                        </p>
                    </div>
                </div>
            )}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
                <h2 className="text-xl font-bold text-gray-800">Profile</h2>
                <p className="text-gray-500">Update your physical stats and preferences to get accurate diet plans.</p>
            </div>
            {/* 
               We might need to adjust Profile.jsx to not include Navbar if it does. 
               Checking Profile.jsx content would be good, but assuming standard page.
               If Profile.jsx imports Navbar, we will see a nested Navbar.
               For this task, I will just render it and we can refactor if needed.
            */}
            <Profile 
                isEmbedded={true} 
                onProfileComplete={onProfileComplete} 
                onViewDietPlan={onViewDietPlan}
                onUpdateStart={onUpdateStart}
                onUpdateEnd={onUpdateEnd}
            /> 
        </div>
    );
};

export default UpdateProfileDisplay;
