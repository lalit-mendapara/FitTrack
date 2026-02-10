import React from 'react';
import { Sparkles, Utensils, Calendar, TrendingDown, PartyPopper } from 'lucide-react';

const FeastModeBanner = ({ event }) => {
    if (!event) return null;

    const isFeastDay = event.status === 'FEAST_DAY';
    
    // Status: BANKING (Reducing calories)
    if (!isFeastDay) {
        return (
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-0.5 shadow-lg mb-6 animate-in fade-in slide-in-from-top-4">
                <div className="bg-white rounded-[14px] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-indigo-50 rounded-xl text-indigo-600">
                            <TrendingDown size={24} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                Feast Mode: Banking Calories
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                    {event.days_remaining} Days Left
                                </span>
                            </h3>
                            <p className="text-gray-600 text-sm mt-1">
                                We're saving <strong>{event.daily_deduction} kcal/day</strong> so you can enjoy 
                                <span className="font-bold text-indigo-600"> {event.event_name} </span> 
                                guilt-free!
                            </p>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-4 bg-gray-50 px-4 py-2 rounded-xl border border-gray-100 min-w-fit">
                        <div className="text-right">
                            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total Banked</p>
                            <p className="text-xl font-black text-indigo-600">
                                {event.target_bank_calories} <span className="text-sm font-normal text-gray-400">kcal</span>
                            </p>
                        </div>
                        <div className="h-8 w-px bg-gray-200"></div>
                        <Calendar size={20} className="text-gray-400" />
                    </div>
                </div>
            </div>
        );
    }

    // Status: FEAST DAY (High calories!)
    return (
        <div className="bg-gradient-to-r from-amber-400 via-orange-500 to-red-500 rounded-2xl p-0.5 shadow-lg mb-6 animate-pulse-slow">
            <div className="bg-white/95 backdrop-blur-sm rounded-[14px] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 -mr-4 -mt-4 opacity-10 transform rotate-12">
                    <Utensils size={120} />
                </div>
                
                <div className="flex items-start gap-4 relative z-10">
                    <div className="p-3 bg-orange-100 rounded-xl text-orange-600">
                        <PartyPopper size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            It's Feast Day: {event.event_name}!
                        </h3>
                        <p className="text-gray-600 text-sm mt-1">
                            Your calorie target is boosted by <strong>+{event.target_bank_calories} kcal</strong> today. 
                            Enjoy your meal!
                        </p>
                    </div>
                </div>
                
                <div className="relative z-10 bg-gradient-to-r from-orange-500 to-red-500 text-white px-6 py-2 rounded-xl shadow-md transform hover:scale-105 transition-transform font-bold text-center">
                    Enjoy! 🍽️
                </div>
            </div>
        </div>
    );
};

export default FeastModeBanner;
