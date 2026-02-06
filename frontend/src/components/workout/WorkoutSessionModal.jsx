import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle2, Save, X, Trophy } from 'lucide-react';

const WorkoutSessionModal = ({ isOpen, onClose, initialDuration = 60, onSave, isSaving }) => {
    const [duration, setDuration] = useState(initialDuration);

    useEffect(() => {
        setDuration(initialDuration);
    }, [initialDuration, isOpen]);

    if (!isOpen) return null;

    const handleSave = () => {
        onSave(parseInt(duration, 10));
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden relative animate-in zoom-in-95 duration-300">
                {/* Header Decoration */}
                <div className="absolute top-0 inset-x-0 h-2 bg-gradient-to-r from-emerald-400 to-teal-500"></div>

                <div className="p-8 text-center">
                    {/* Success Icon */}
                    <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6 text-emerald-600 shadow-xl shadow-emerald-100">
                        <Trophy size={40} className="fill-current" />
                    </div>

                    <h2 className="text-2xl font-black text-gray-900 mb-2">Workout Complete!</h2>
                    <p className="text-gray-500 font-medium mb-8">Great job crushing your goals today.</p>

                    {/* Duration Input Section */}
                    <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100 mb-8">
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                            Session Duration
                        </label>
                        <div className="flex items-center justify-center gap-4">
                            <button 
                                onClick={() => setDuration(Math.max(5, duration - 5))}
                                className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-gray-500 hover:bg-gray-100 flex items-center justify-center font-bold text-xl shadow-sm transition-colors"
                            >
                                -
                            </button>
                            
                            <div className="flex items-baseline gap-1">
                                <span className="text-5xl font-black text-gray-900 tracking-tight">
                                    {duration}
                                </span>
                                <span className="text-gray-500 font-bold">min</span>
                            </div>

                            <button 
                                onClick={() => setDuration(duration + 5)}
                                className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-gray-500 hover:bg-gray-100 flex items-center justify-center font-bold text-xl shadow-sm transition-colors"
                            >
                                +
                            </button>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 py-3.5 px-4 bg-white border border-gray-200 text-gray-600 font-bold rounded-xl hover:bg-gray-50 transition-colors"
                            disabled={isSaving}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="flex-[2] py-3.5 px-4 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl shadow-lg shadow-emerald-200 transition-all transform active:scale-95 flex items-center justify-center gap-2"
                        >
                            {isSaving ? (
                                <>
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save size={20} />
                                    Save Session
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WorkoutSessionModal;
