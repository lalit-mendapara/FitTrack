import React from 'react';
import { Info } from 'lucide-react';

const NoticeBox = () => {
    const messages = [
        "Track your fitness journey with diet and workout.",
        "After changing profile you need to update your diet plan and workout plan.",
        "You will get desired output only on consistent efforts.",
        "Track your Journey with Logged meals and Exercieses."
    ];

    // Combine all messages with | separator and reduced equal spaces on both sides using non-breaking spaces
    const combinedMessage = messages.join("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;");

    // Show on all screen sizes
    return (
        <div className="block w-full">
            <div className="bg-linear-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-3 relative overflow-hidden">
                <div className="flex items-center justify-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg shrink-0">
                        <Info size={18} className="text-blue-600" />
                    </div>
                    <div className="overflow-hidden flex-1">
                        <div 
                            className="whitespace-nowrap"
                            style={{
                                animation: 'marquee 45s linear infinite',
                                display: 'inline-block'
                            }}
                        >
                            <span 
                                className="text-sm font-medium text-blue-800"
                                dangerouslySetInnerHTML={{ __html: combinedMessage }}
                            />
                        </div>
                    </div>
                </div>
            </div>
            
            {/* Add global styles for marquee animation */}
            <style dangerouslySetInnerHTML={{
                __html: `
                    @keyframes marquee {
                        0% {
                            transform: translateX(100%);
                        }
                        100% {
                            transform: translateX(-100%);
                        }
                    }
                `
            }} />
        </div>
    );
};

export default NoticeBox;
