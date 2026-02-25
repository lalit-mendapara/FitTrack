import React, { useState } from 'react';
import { Utensils, Calendar, XCircle } from 'lucide-react';
import feastModeService from '../../api/feastModeService';
import feastLogo from '../../images/Feast-logo98_png586.png';
import ConfirmModal from '../common/ConfirmModal';

const FeastModeBanner = ({ event, onUpdate }) => {
    const [loading, setLoading] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    if (!event) return null;

    const handleCancelClick = () => {
        setShowConfirm(true);
    };

    const confirmCancel = async () => {
        setLoading(true);
        try {
            await feastModeService.cancel();
            if (onUpdate) onUpdate();
            setShowConfirm(false);
        } catch (error) {
            console.error("Failed to cancel feast mode", error);
            // Ideally use a toast here instead of alert, but keeping minimal changes
            alert("Failed to cancel. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const isFeastDay = event.status === 'FEAST_DAY';
    
    // Status: BANKING (Reducing calories)
    if (!isFeastDay) {
        return (
            <>
                <div className="bg-linear-to-r from-purple-600 to-indigo-600 rounded-2xl p-0.5 shadow-lg mb-6 animate-in fade-in slide-in-from-top-4">
                    <div className="bg-white rounded-[14px] p-3 sm:p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="flex items-start gap-3">
                            <div className="p-2 bg-indigo-50 rounded-xl shrink-0">
                                <img src={feastLogo} alt="Feast Mode" className="h-8 w-8 sm:h-9 sm:w-9 object-contain" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="text-base sm:text-lg font-bold text-gray-900 flex items-center gap-2 flex-wrap">
                                    Feast Mode: Banking Calories
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                        {event.days_remaining} Days Left
                                    </span>
                                </h3>
                                <p className="text-gray-600 text-sm mt-1 wrap-break-word">
                                    We're saving <strong>{event.daily_deduction} kcal/day</strong> so you can enjoy 
                                    <span className="font-bold text-indigo-600 wrap-break-word"> {event.event_name} </span> 
                                    guilt-free!
                                </p>
                            </div>
                        </div>
                        
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                            <div className="flex items-center gap-3 bg-gray-50 px-3 py-2 rounded-xl border border-gray-100 justify-center">
                                <div className="text-center">
                                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total Banked</p>
                                    <p className="text-lg sm:text-xl font-black text-indigo-600">
                                        {event.target_bank_calories} <span className="text-sm font-normal text-gray-400">kcal</span>
                                    </p>
                                </div>
                                <div className="h-6 w-px bg-gray-200 hidden sm:block"></div>
                                <Calendar size={18} className="text-gray-400 shrink-0" />
                            </div>

                            <button 
                                onClick={handleCancelClick}
                                disabled={loading}
                                className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-colors disabled:opacity-50 shrink-0"
                            >
                                <XCircle size={16} /> Cancel
                            </button>
                        </div>
                    </div>
                </div>

                <ConfirmModal 
                    isOpen={showConfirm}
                    onClose={() => !loading && setShowConfirm(false)}
                    onConfirm={confirmCancel}
                    title="Cancel Feast Mode?"
                    message={`Are you sure you want to cancel "${event.event_name}"? \n\nThis will restore your original calorie targets and workout plan. All banked progress will be lost.`}
                    confirmText="Yes, Cancel Setup"
                    cancelText="Keep Feast Mode"
                    isDangerous={true}
                    isLoading={loading}
                />
            </>
        );
    }

    // Status: FEAST DAY (High calories!)
    return (
        <>
            <div className="bg-linear-to-r from-amber-400 via-orange-500 to-red-500 rounded-2xl p-0.5 shadow-lg mb-6 animate-pulse-slow">
                <div className="bg-white/95 backdrop-blur-sm rounded-[14px] p-3 sm:p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 relative overflow-hidden">
                    <div className="absolute top-0 right-0 -mr-4 -mt-4 opacity-10 transform rotate-12">
                        <Utensils size={80} className="sm:size-120" />
                    </div>
                    
                    <div className="flex items-start gap-3 relative z-10">
                        <div className="p-2 bg-orange-100 rounded-xl shrink-0">
                            <img src={feastLogo} alt="Feast Mode" className="h-8 w-8 sm:h-9 sm:w-9 object-contain" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="text-base sm:text-lg font-bold text-gray-900 flex items-center gap-2 flex-wrap">
                                🎉 It's Feast Day: {event.event_name}!
                            </h3>
                            <p className="text-gray-600 text-sm mt-1 wrap-break-word">
                                Your banked <strong>+{event.target_bank_calories} kcal</strong> are added into today's plan — enjoy your feast day without any hesitation!
                            </p>
                            <p className="text-gray-400 text-xs mt-1">
                                Macros are as per your regular plan.
                            </p>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-3 relative z-10">
                        <div className="bg-linear-to-r from-orange-500 to-red-500 text-white px-4 py-2 sm:px-6 rounded-xl shadow-md transform hover:scale-105 transition-transform font-bold text-center">
                            Enjoy! 🍽️
                        </div>
                         <button 
                            onClick={handleCancelClick}
                            disabled={loading}
                            className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-gray-500 hover:text-red-600 bg-white/50 hover:bg-white rounded-lg transition-colors shrink-0"
                            title="Cancel Feast Day (Revert to normal)"
                        >
                            <XCircle size={16} />
                        </button>
                    </div>
                </div>
            </div>

            <ConfirmModal 
                isOpen={showConfirm}
                onClose={() => !loading && setShowConfirm(false)}
                onConfirm={confirmCancel}
                title="End Feast Day Early?"
                message={`Are you sure you want to end "${event.event_name}" early? \n\nThis will revert your daily calorie target to normal.`}
                confirmText="End Feast Day"
                cancelText="Keep Enjoying"
                isDangerous={true}
                isLoading={loading}
            />
        </>
    );
};

export default FeastModeBanner;
