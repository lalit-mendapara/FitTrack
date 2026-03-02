import React, { useState, useEffect, useRef } from 'react';
import { X, PartyPopper } from 'lucide-react';
import FeastActivateModal from './FeastActivateModal';

const WeeklyFeastNotification = ({ onFeastActivated }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const initialized = useRef(false);

    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;

        const today = new Date();
        // 0 = Sunday, 1 = Monday
        if (today.getDay() === 1) {
            const dateStr = today.toISOString().split('T')[0];
            const storageKey = `feast_prompt_${dateStr}`;
            
            const hasSeen = localStorage.getItem(storageKey);
            if (!hasSeen) {
                setIsVisible(true);
                // Immediately set flag so it won't appear on subsequent logins / reloads today
                localStorage.setItem(storageKey, 'true');
            }
        }
    }, []);

    const handleDismiss = () => {
        setIsVisible(false);
    };

    if (!isVisible) return null;

    return (
        <>
            <div className="bg-linear-to-r from-indigo-500 to-purple-600 rounded-2xl p-4 shadow-lg mb-6 text-white flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in slide-in-from-top-4">
                <div className="flex items-start gap-3">
                    <div className="p-2 bg-white/20 rounded-xl shrink-0 backdrop-blur-sm">
                        <PartyPopper size={24} className="text-white" />
                    </div>
                    <div>
                        <h3 className="text-base sm:text-lg font-bold flex items-center gap-2">
                            Plan Ahead for the Week!
                        </h3>
                        <p className="text-white/90 text-sm mt-1">
                            If you have any Party or are Unable to follow the schedule. 
                            Please Activate Feast Mode.
                        </p>
                    </div>
                </div>
                
                <div className="flex items-center gap-3 shrink-0 ml-auto md:ml-0">
                    <button 
                        onClick={() => setShowModal(true)}
                        className="px-4 py-2 bg-white text-indigo-600 font-bold text-sm rounded-xl hover:bg-indigo-50 transition-colors shadow-sm whitespace-nowrap"
                    >
                        Activate Feast Mode
                    </button>
                    <button 
                        onClick={handleDismiss}
                        className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
                        aria-label="Dismiss"
                    >
                        <X size={20} />
                    </button>
                </div>
            </div>

            {showModal && (
                <FeastActivateModal 
                    onClose={() => setShowModal(false)}
                    onSuccess={() => {
                        setShowModal(false);
                        setIsVisible(false); // Hide the notification row
                        if (onFeastActivated) onFeastActivated();
                    }}
                />
            )}
        </>
    );
};

export default WeeklyFeastNotification;
