import React from 'react';
import { Home, Utensils, Dumbbell, User, Bot, Sparkles } from 'lucide-react';

const MobileBottomNav = ({ activeTab, onTabChange }) => {
  const navItems = [
    { id: 'dashboard-overview', label: 'Home', icon: Home },
    { id: 'diet-plan', label: 'Diet', icon: Utensils },
    { id: 'workout-plan', label: 'Workout', icon: Dumbbell },
    { id: 'ai-coach', label: 'Coach', icon: Bot }, // Using Bot instead of MessageSquare for variety
    { id: 'profile', label: 'Profile', icon: User },
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
              className={`flex flex-col items-center justify-center w-full gap-1 transition-all duration-300 ${isActive ? 'text-indigo-600 -translate-y-1' : 'text-gray-400 hover:text-gray-600'}`}
            >
              <div className={`
                relative p-1.5 rounded-2xl transition-all duration-300
                ${isActive ? 'bg-indigo-50 shadow-sm' : 'bg-transparent'}
              `}>
                <Icon size={isActive ? 24 : 22} strokeWidth={isActive ? 2.5 : 2} />
                {isActive && (
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
