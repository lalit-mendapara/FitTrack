import React from 'react';
import { Home, Utensils, Dumbbell, User, Bot, Sparkles } from 'lucide-react';

const MobileBottomNav = ({ 
    activeTab, 
    onTabChange,
    hasPhysicalProfile,
    hasWorkoutPreferences,
    hasDietPlan,
    hasWorkoutPlan,
    loadingProfile
}) => {
  const navItems = [
    { 
        id: 'dashboard-overview', 
        label: 'Home', 
        icon: Home,
        locked: !hasDietPlan && !hasWorkoutPlan && !loadingProfile
    },
    { 
        id: 'diet-plan', 
        label: 'Diet', 
        icon: Utensils,
        locked: !hasPhysicalProfile && !loadingProfile
    },
    { 
        id: 'workout-plan', 
        label: 'Workout', 
        icon: Dumbbell,
        locked: (!hasPhysicalProfile || !hasWorkoutPreferences) && !loadingProfile
    },
    { 
        id: 'ai-coach', 
        label: 'Coach', 
        icon: Bot,
        locked: !hasDietPlan && !hasWorkoutPlan && !loadingProfile
    },
    { 
        id: 'profile', 
        label: 'Profile', 
        icon: User,
        locked: false
    },
  ];

  return (
    <div className="fixed bottom-0 left-0 w-full bg-white/80 backdrop-blur-xl border-t border-gray-100 pb-safe-area-bottom z-50 md:hidden transition-all duration-300">
      <div className="flex justify-around items-center px-2 py-3">
        {navItems.map((item) => {
          const isActive = activeTab === item.id || (activeTab === 'dashboard' && item.id === 'dashboard-overview');
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`relative flex flex-col items-center justify-center w-full gap-1 transition-all duration-300 ${isActive ? 'text-indigo-600 -translate-y-1' : 'text-gray-400 hover:text-gray-600'} ${item.locked ? 'opacity-50' : ''}`}
            >
              <div className={`
                relative p-1.5 rounded-2xl transition-all duration-300
                ${isActive ? 'bg-indigo-50 shadow-sm' : 'bg-transparent'}
              `}>
                <Icon size={isActive ? 24 : 22} strokeWidth={isActive ? 2.5 : 2} />
                {item.locked && (
                   <div className="absolute -bottom-1 -right-1 bg-white rounded-full p-0.5 shadow-sm">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                   </div>
                )}
                {isActive && !item.locked && (
                    <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
                    </span>
                )}
              </div>
              <span className={`text-[10px] font-bold tracking-wide ${isActive ? 'text-indigo-600' : 'text-gray-400'}`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default MobileBottomNav;
