import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useProfile } from '../hooks/useProfile'; // Hook Import
import Profile from './Profile';
import DietPlan from './DietPlan';
import WorkoutPlan from './WorkoutPlan'; 
import UpdateUserInfo from '../components/profile/UpdateUserInfo';
import UpdateProfileDisplay from '../components/profile/UpdateProfileDisplay';
import UserProfileDisplay from '../components/profile/UserProfileDisplay';
import DashboardOverview from '../components/dashboard/DashboardOverview';
import AICoach from './AICoach';
import MobileBottomNav from '../components/layout/MobileBottomNav';
import logo from '../images/Frame 13 2 (2).png';
import { debounce } from '../utils/debounce';

const Dashboard = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const activeSection = searchParams.get('tab') || 'profile';
    const { 
        hasPhysicalProfile, 
        hasWorkoutPreferences, 
        hasDietPlan,
        hasWorkoutPlan,
        loading: loadingProfile, 
        setHasPhysicalProfile, 
        setHasWorkoutPreferences,
        refreshProfileStatus 
    } = useProfile();

    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false); // Global blocking state

    // Close mobile menu on resize to desktop
    React.useEffect(() => {
        const handleResize = debounce(() => {
             if (window.innerWidth >= 768) {
                setIsMobileMenuOpen(false);
            }
        }, 200);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // NEW: Auto-redirect to Create Profile if missing
    React.useEffect(() => {
        if (!loadingProfile && !hasPhysicalProfile && activeSection !== 'update-profile') {
            // Replace history to avoid back-button loops or just set params
            setSearchParams({ tab: 'update-profile' }, { replace: true });
        } else if (!loadingProfile && hasPhysicalProfile && (hasDietPlan || hasWorkoutPlan) && (!searchParams.get('tab') || searchParams.get('tab') === 'profile')) {
            // New logic: Existing users (with at least one plan) redirect to dashboard overview
             setSearchParams({ tab: 'dashboard-overview' }, { replace: true });
        }
    }, [loadingProfile, hasPhysicalProfile, activeSection, setSearchParams]);

    const [isSettingsOpen, setIsSettingsOpen] = useState(false); // Settings menu state
    const settingsRef = React.useRef(null); // Ref for closing menu on outside click

    // Close settings menu when clicking outside
    React.useEffect(() => {
        const handleClickOutside = (event) => {
            if (settingsRef.current && !settingsRef.current.contains(event.target)) {
                setIsSettingsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);




    const handleLogout = async () => {
        await logout();
        toast.success("Logged out successfully");
        navigate('/');
    };

    const handleProfileComplete = (updateType) => {
        // Only redirect to diet plan if this is a NEW profile creation (was previously missing)
        if (updateType === 'physical' && hasPhysicalProfile === false) {
            setSearchParams({ tab: 'diet-plan' });
        }

        // Only redirect to workout plan if this is a NEW workout preference creation (was previously missing)
        if (updateType === 'workout' && hasWorkoutPreferences === false) {
            setSearchParams({ tab: 'workout-plan' });
        }

        setHasPhysicalProfile(true);
        refreshProfileStatus();
    };

    const renderContent = () => {
        switch (activeSection) {
            case 'profile':
                return <UserProfileDisplay 
                           user={user} 
                           isProfileMissing={!hasPhysicalProfile && !loadingProfile}
                           onLogout={handleLogout}
                           onUpdateProfile={() => setSearchParams({ tab: 'update-profile' })}
                       />;
            case 'update-profile':
                return <UpdateProfileDisplay 
                           user={user} 
                           isProfileMissing={!hasPhysicalProfile && !loadingProfile}
                           onProfileComplete={handleProfileComplete}
                           onViewDietPlan={() => setSearchParams({ tab: 'diet-plan' })}
                           onUpdateStart={() => setIsUpdating(true)}
                           onUpdateEnd={() => setIsUpdating(false)}
                       />;
            case 'diet-plan':
                if (loadingProfile) return <div>Loading...</div>;
                if (!hasPhysicalProfile) {
                    // Redirect logic if somehow they got here
                    return <UpdateProfileDisplay 
                               user={user} 
                               isProfileMissing={true}
                               onProfileComplete={handleProfileComplete}
                               onViewDietPlan={() => setSearchParams({ tab: 'diet-plan' })}
                               onUpdateStart={() => setIsUpdating(true)}
                               onUpdateEnd={() => setIsUpdating(false)}
                           />;
                }
                return <DietPlan 
                           isEmbedded={true} 
                           onGenerateStart={() => setIsUpdating(true)}
                           onGenerateEnd={() => setIsUpdating(false)}
                       />;
            case 'workout-plan':
                if (loadingProfile) return <div>Loading...</div>;
                // Reuse the same logic for blocking if profile or preferences are missing
                if (!hasPhysicalProfile || !hasWorkoutPreferences) {
                     return <UpdateProfileDisplay 
                                user={user} 
                                isProfileMissing={!hasPhysicalProfile} // If physical is missing, priority
                                // Note: UpdateProfileDisplay handles alerting.
                                onProfileComplete={handleProfileComplete} // This re-checks logic
                                onViewDietPlan={() => setSearchParams({ tab: 'diet-plan' })}
                                onUpdateStart={() => setIsUpdating(true)}
                                onUpdateEnd={() => setIsUpdating(false)}
                            />;
                }
                return <WorkoutPlan 
                           isEmbedded={true}
                           onGenerateStart={() => setIsUpdating(true)}
                           onGenerateEnd={() => setIsUpdating(false)}
                       />;
            case 'ai-coach':
                return <AICoach />;
            case 'dashboard-overview':
                return <DashboardOverview hasDietPlan={hasDietPlan} hasWorkoutPlan={hasWorkoutPlan} />;
            default:
                return <UserProfileDisplay 
                           user={user} 
                           isProfileMissing={!hasPhysicalProfile && !loadingProfile}
                           onLogout={handleLogout}
                           onUpdateProfile={() => setSearchParams({ tab: 'update-profile' })}
                       />;
        }
    };

    const navItems = [
        { 
            id: 'dashboard-overview', 
            label: 'Dashboard',
            locked: !hasDietPlan && !hasWorkoutPlan && !loadingProfile
        },
        { 
            id: 'diet-plan', 
            label: 'Diet Plan',
            locked: !hasPhysicalProfile && !loadingProfile 
        },
        { 
            id: 'workout-plan', 
            label: 'Workout Plan',
            locked: (!hasPhysicalProfile || !hasWorkoutPreferences) && !loadingProfile 
        },
        { 
            id: 'ai-coach', 
            label: 'AI Coach',
            locked: !hasDietPlan && !hasWorkoutPlan && !loadingProfile
        },
    ];

    const handleSettingsClick = (action) => {
        setIsSettingsOpen(false);
        if (action === 'logout') {
            handleLogout();
        } else {
            setSearchParams({ tab: action });
        }
    };

    return (
        <div className="flex h-screen bg-gray-50">
            {/* Global Blocking Overlay */}
            {isUpdating && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex flex-col items-center justify-center p-4">
                    <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-2xl transform scale-100 transition-all">
                        <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">Generating Plan</h3>
                        <p className="text-gray-600">
                            Please wait while we generate your personalized plan. This may take a few moments...
                        </p>
                    </div>
                </div>
            )}

            {/* Sidebar - Hidden on Mobile */}
            <div className="hidden md:flex fixed inset-y-0 left-0 z-30 w-64 bg-white shadow-xl flex-col transition-transform duration-300 ease-in-out md:relative md:translate-x-0">
                <div className="p-6 border-b border-gray-100 flex items-center justify-between md:justify-center gap-3">
                     <img 
                        src={logo} 
                        alt="FitTrack Logo" 
                        className="h-8 w-auto object-contain rounded-md" 
                     />
                     <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
                        FitTrack
                    </h1>
                </div>

                <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => {
                                if (item.locked) {
                                    if (item.id === 'workout-plan' && hasPhysicalProfile && !hasWorkoutPreferences) {
                                        toast.info("Please set your Workout Preferences in Profile to access this.", {
                                            autoClose: 3000
                                        });
                                        setSearchParams({ tab: 'update-profile' });
                                    } else if ((item.id === 'dashboard-overview' || item.id === 'ai-coach') && (!hasDietPlan && !hasWorkoutPlan)) {
                                         toast.info("Please generate a Diet Plan or Workout Plan to unlock the Dashboard and AI Coach.", {
                                            autoClose: 3000
                                        });
                                         // Redirect to diet plan if available, else profile (handled by profile check)
                                         if (hasPhysicalProfile) {
                                             setSearchParams({ tab: 'diet-plan' });
                                         }
                                    }
                                    return;
                                }
                                setSearchParams({ tab: item.id });
                            }}
                            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 text-sm font-medium ${
                                activeSection === item.id
                                    ? 'bg-indigo-50 text-indigo-700 shadow-sm ring-1 ring-indigo-200'
                                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                            } ${item.locked ? 'opacity-50 cursor-not-allowed hover:bg-transparent' : ''}`}
                        >
                            <span>{item.label}</span>
                            {item.locked && (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            )}
                        </button>
                    ))}
                </nav>

                <div className="p-4 border-t border-gray-100 bg-gray-50/50" ref={settingsRef}>
                    <div className="relative">
                        {/* Drop-up Menu */}
                        {isSettingsOpen && (
                            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden transform origin-bottom transition-all">
                                <button
                                    onClick={() => handleSettingsClick('profile')}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                    Account
                                </button>
                                <button
                                    onClick={() => handleSettingsClick('update-profile')}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                                    </svg>
                                    Profile
                                </button>
                                <div className="h-px bg-gray-100 my-1"></div>
                                <button
                                    onClick={() => handleSettingsClick('logout')}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-600 hover:bg-red-50 transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                    </svg>
                                    Logout
                                </button>
                            </div>
                        )}

                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 px-2">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-md">
                                    {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
                                </div>
                                <div className="flex flex-col overflow-hidden max-w-[100px]">
                                    <span className="text-sm font-bold text-gray-900 truncate">{user?.name}</span>
                                    <span className="text-xs text-gray-500 truncate">{user?.email}</span>
                                </div>
                            </div>
                            <button
                                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                                className={`p-2 rounded-lg transition-colors ${isSettingsOpen ? 'bg-indigo-100 text-indigo-600' : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'}`}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden flex flex-col relative w-full">
                {/* Mobile Bottom Navigation */}
                <MobileBottomNav 
                    activeTab={activeSection} 
                    onTabChange={(id) => setSearchParams({ tab: id })} 
                />

                <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-4 md:p-10 pb-24 md:pb-10">
                    <div className="max-w-full mx-auto space-y-6 animate-fadeIn">
                       {renderContent()}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default Dashboard;
