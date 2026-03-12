import React, { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, Dumbbell, Apple } from 'lucide-react';
import { useNavigationBlocker } from '../../hooks/useNavigationBlocker';
import { useAuth } from '../../context/AuthContext';

// Import diet images
import vegBowl from '../../assets/diet/veg/veg_bowl.jpeg';
import vegSalad from '../../assets/diet/veg/veg_salad.jpeg';
import greenVegies from '../../assets/diet/veg/green_vegies.jpeg';
import paneerCurry from '../../assets/diet/veg/paneer_curry.jpeg';
import dalChawal from '../../assets/diet/veg/DalChawal.webp';

import chickenCurry from '../../assets/diet/nonveg/chiken_curry.jpeg';
import grilledChicken from '../../assets/diet/nonveg/grilled_chicken.jpeg';
import grilledFish from '../../assets/diet/nonveg/grilled_fish.jpeg';
import eggBhurji from '../../assets/diet/nonveg/egg_bhurji.jpeg';
import eggFry from '../../assets/diet/nonveg/egg_fry.jpeg';

// Import workout GIFs
import burpee from '../../assets/workout/BURPEE.gif';
import running from '../../assets/workout/RUNNING.gif';
import jumpRope from '../../assets/workout/JUMP_ROPE.gif';
import legPress from '../../assets/workout/LEG_PRESS-1.gif';
import dumbbellCurl from '../../assets/workout/DB_BC_CURL.gif';

const VEG_IMAGES = [vegBowl, vegSalad, greenVegies, paneerCurry, dalChawal];
const NONVEG_IMAGES = [chickenCurry, grilledChicken, grilledFish, eggBhurji, eggFry];
const WORKOUT_GIFS = [burpee, running, jumpRope, legPress, dumbbellCurl];

const GenerationOverlay = ({ 
    isVisible, 
    steps = [], 
    currentStepIndex = 0, 
    isSuccess = false,
    title = "Please Wait",
    successTitle = "All Set!",
    type = "diet" // 'diet' or 'workout' for icon selection
}) => {
    const { user } = useAuth();
    const [currentImageIndex, setCurrentImageIndex] = useState(0);
    
    useNavigationBlocker(isVisible);

    // Rotate images every 2 seconds during loading
    useEffect(() => {
        if (!isVisible || isSuccess) return;
        
        const interval = setInterval(() => {
            setCurrentImageIndex((prev) => {
                if (type === 'diet') {
                    const images = user?.profile?.diet_type === 'non-veg' ? NONVEG_IMAGES : VEG_IMAGES;
                    return (prev + 1) % images.length;
                } else {
                    return (prev + 1) % WORKOUT_GIFS.length;
                }
            });
        }, 2000);
        
        return () => clearInterval(interval);
    }, [isVisible, isSuccess, type, user]);
    
    if (!isVisible) return null;

    const Icon = type === 'workout' ? Dumbbell : Apple;
    
    // Get current image based on type and user preference
    const getCurrentImage = () => {
        if (type === 'diet') {
            const images = user?.profile?.diet_type === 'non-veg' ? NONVEG_IMAGES : VEG_IMAGES;
            return images[currentImageIndex];
        } else {
            return WORKOUT_GIFS[currentImageIndex];
        }
    };

    return (
        <div className="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300 pointer-events-auto cursor-wait">
           <div className="bg-white rounded-2rem p-10 shadow-2xl flex flex-col items-center gap-6 max-w-sm w-full border border-white/20 relative overflow-hidden">
               
               {/* Background decoration */}
               <div className="absolute top-0 inset-x-0 h-1 bg-linear-to-r from-indigo-500 via-purple-500 to-pink-500 animate-gradient-x"></div>
               
               {isSuccess ? (
                 <div className="w-20 h-20 bg-green-100/50 rounded-full flex items-center justify-center text-green-500 animate-in zoom-in duration-300">
                    <div className="relative">
                        <div className="absolute inset-0 bg-green-200 rounded-full animate-ping opacity-20"></div>
                        <CheckCircle size={48} strokeWidth={3} />
                    </div>
                 </div>
               ) : (
                 <div className="relative flex flex-col items-center">
                    {/* Rotating Image/GIF */}
                    <div className="w-32 h-32 mb-4 rounded-2xl overflow-hidden shadow-lg border-4 border-indigo-100 animate-in zoom-in duration-500">
                        <img 
                            src={getCurrentImage()} 
                            alt={type === 'diet' ? 'Food' : 'Workout'}
                            className="w-full h-full object-cover"
                            key={currentImageIndex}
                        />
                    </div>
                    {/* Spinner overlay */}
                    <div className="relative">
                        <div className="w-16 h-16 border-4 border-indigo-100 rounded-full animate-spin"></div>
                        <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                        <div className="absolute inset-0 flex items-center justify-center">
                           <RefreshCw size={20} className="text-indigo-600 animate-pulse" />
                        </div>
                    </div>
                 </div>
               )}

               <div className="text-center space-y-2">
                  <h3 className="text-2xl font-black text-gray-800 animate-pulse">
                     {isSuccess ? successTitle : title}
                  </h3>
                  <p className="text-gray-500 font-medium text-lg min-w-200px">
                     {steps[currentStepIndex]}
                     {!isSuccess && <span className="animate-pulse">...</span>}
                  </p>
               </div>

           </div>
        </div>
    );
};

export default GenerationOverlay;
