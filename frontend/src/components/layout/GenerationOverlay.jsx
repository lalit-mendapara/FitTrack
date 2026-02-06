import React, { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, Dumbbell, Apple } from 'lucide-react';
import { useNavigationBlocker } from '../../hooks/useNavigationBlocker';

const GenerationOverlay = ({ 
    isVisible, 
    steps = [], 
    currentStepIndex = 0, 
    isSuccess = false,
    title = "Please Wait",
    successTitle = "All Set!",
    type = "diet" // 'diet' or 'workout' for icon selection
}) => {
    
    // Activate blocking when visible and not yet success (or even during success delay?)
    // Requirement says "until plan is not generated". 
    // Once success message shows, we usually wait 2s then close. 
    // We should probably keep blocking until it fully closes.
    useNavigationBlocker(isVisible);

    // Local cycle state for steps not strictly driven by parent?
    // The parent controls the index, but let's ensure we render smoothly.
    
    // Render nothing if not visible
    if (!isVisible) return null;

    const Icon = type === 'workout' ? Dumbbell : Apple; // Or RefreshCw generic

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300 pointer-events-auto cursor-wait">
           {/* Prevent any clicks passing through with full screen blocking div above */}
           
           <div className="bg-white rounded-[2rem] p-10 shadow-2xl flex flex-col items-center gap-6 max-w-sm w-full border border-white/20 relative overflow-hidden">
               
               {/* Background decoration */}
               <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 animate-gradient-x"></div>
               
               {isSuccess ? (
                 <div className="w-20 h-20 bg-green-100/50 rounded-full flex items-center justify-center text-green-500 animate-in zoom-in duration-300">
                    <div className="relative">
                        <div className="absolute inset-0 bg-green-200 rounded-full animate-ping opacity-20"></div>
                        <CheckCircle size={48} strokeWidth={3} />
                    </div>
                 </div>
               ) : (
                 <div className="relative">
                    <div className="w-20 h-20 border-4 border-indigo-100 rounded-full animate-spin"></div>
                    <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                       <RefreshCw size={24} className="text-indigo-600 animate-pulse" />
                    </div>
                 </div>
               )}

               <div className="text-center space-y-2">
                  <h3 className="text-2xl font-black text-gray-800 animate-pulse">
                     {isSuccess ? successTitle : title}
                  </h3>
                  <p className="text-gray-500 font-medium text-lg min-w-[200px]">
                     {steps[currentStepIndex]}
                     {!isSuccess && <span className="animate-pulse">...</span>}
                  </p>
               </div>

           </div>
        </div>
    );
};

export default GenerationOverlay;
