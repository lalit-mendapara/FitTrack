import React from 'react';
import { Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const LockOverlay = ({ 
    isLocked, 
    message = "Access Restricted", 
    actionLink, 
    actionLabel = "Unlock",
    children 
}) => {
    const navigate = useNavigate();

    // If not locked, just render children normally
    if (!isLocked) {
        return <>{children}</>;
    }

    return (
        <div className="relative h-full w-full rounded-2xl overflow-hidden group">
            {/* Blurred Content */}
            <div className="filter blur-[6px] pointer-events-none select-none h-full transition-all duration-500 opacity-60">
                {children}
            </div>

            {/* Overlay */}
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-6 bg-white/30 backdrop-blur-sm animate-in fade-in duration-500">
                <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl shadow-xl border border-white/50 text-center max-w-sm w-[90%] transform transition-transform hover:scale-105 duration-300">
                    <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 text-indigo-600 shadow-sm">
                        <Lock size={24} />
                    </div>
                    
                    <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-2">
                        {message}
                    </h3>
                    
                    {actionLink && (
                        <button
                            onClick={() => navigate(actionLink)}
                            className="mt-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 transition-all hover:shadow-xl active:scale-95"
                        >
                            {actionLabel}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LockOverlay;
