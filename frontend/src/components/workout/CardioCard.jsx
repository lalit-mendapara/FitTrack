import React from 'react';
import { HeartPulse, Flame, CheckCircle, RotateCcw } from 'lucide-react';
import { logWorkout, deleteWorkoutLog } from '../../api/tracking';
import { toast } from 'react-toastify';
import { useState, useEffect } from 'react';

const CardioCard = ({ exercise, initialLogId = null, targetDate = null, onLogUpdate }) => {
    // State to track if logged locally (and store the ID)
    const [logId, setLogId] = useState(initialLogId);

    // Sync
    useEffect(() => {
        setLogId(initialLogId);
    }, [initialLogId]);

    const handleLogToggle = async () => {
          try {
              if (logId) {
                  // UNLOG
                  await deleteWorkoutLog(logId);
                  setLogId(null);
                  toast.info(`Unlogged ${exercise.exercise}`);
              } else {
                  // LOG
                  const res = await logWorkout({
                      exercise_name: exercise.exercise,
                      date: targetDate || new Date().toISOString().split('T')[0],
                      duration_min: typeof exercise.duration === 'string' ? parseInt(exercise.duration) : exercise.duration,
                      calories_burned: exercise.calories_burned,
                      img_url: exercise.image_url
                  });
                  setLogId(res.log_id);
                  toast.success(`Logged ${exercise.exercise}!`);
              }
              // Trigger refresh
              if (onLogUpdate) onLogUpdate();

          } catch (e) {
              toast.error("Failed to update log.");
          }
    };

    return (
        <div className="bg-orange-50/50 border border-orange-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col h-full group relative">
            
            {/* Cardio Badge */}
            <div className="absolute top-3 left-3 z-10 flex gap-2">
                <span className="px-2 py-1 bg-orange-500 text-white text-[10px] font-black uppercase tracking-wider rounded-md shadow-sm flex items-center gap-1">
                    <HeartPulse size={12} className="fill-current" />
                    Cardio
                </span>
                {exercise.calories_burned > 0 && (
                    <span className="px-2 py-1 bg-red-500 text-white text-[10px] font-black uppercase tracking-wider rounded-md shadow-sm flex items-center gap-1">
                        <Flame size={12} className="fill-current" />
                        {exercise.calories_burned} kcal
                    </span>
                )}
            </div>

            {/* Image / Placeholder */}
            <div className="h-64 bg-white relative overflow-hidden flex items-center justify-center border-b border-orange-100">
                    {exercise.image_url ? (
                        <img 
                        src={exercise.image_url} 
                        alt={exercise.exercise}
                        className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-500 mix-blend-multiply"
                        />
                    ) : (
                        <div className="text-orange-200">
                            <HeartPulse size={48} />
                        </div>
                    )}
                    {/* Intensity Badge */}
                    {exercise.intensity && (
                        <div className="absolute top-3 right-3 px-2 py-1 bg-white/90 backdrop-blur-sm text-orange-700 text-xs font-bold rounded-lg border border-orange-100 shadow-sm">
                            {exercise.intensity}
                        </div>
                    )}
            </div>

            {/* Content */}
            <div className="p-5 flex-1 flex flex-col">
                <div className="flex justify-between items-start mb-3">
                    <h3 className="text-xl font-black text-gray-900 leading-tight line-clamp-2">{exercise.exercise}</h3>
                </div>

                {/* Always Show Instructions - No Toggle */}
                <div className="mb-4 bg-orange-50 rounded-xl p-3 border border-orange-100/50">
                    {exercise.instructions ? (
                        Array.isArray(exercise.instructions) ? (
                            <ul className="space-y-2">
                                {exercise.instructions.map((point, idx) => (
                                    <li key={idx} className="flex gap-2 text-xs text-gray-600 leading-relaxed font-medium">
                                        <span className="flex-shrink-0 w-1 h-1 rounded-full bg-orange-400 mt-1.5"></span>
                                        {point}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-xs text-gray-600 leading-relaxed font-medium">
                                {exercise.instructions}
                            </p>
                        )
                    ) : (
                        <p className="text-xs text-gray-500 italic text-center py-1">No instructions available.</p>
                    )}
                </div>
                
                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-2 mt-auto pt-4 relative z-0">
                    <div className="bg-white rounded-xl p-2 py-3 border border-orange-100 text-center shadow-sm flex flex-col justify-center">
                        <div className="text-base font-bold text-gray-900">{exercise.duration}</div>
                        <div className="text-[10px] font-bold text-orange-400 uppercase tracking-widest mt-0.5">Duration</div>
                    </div>
                        <div className="bg-white rounded-xl p-2 py-3 border border-orange-100 text-center shadow-sm flex flex-col justify-center">
                        <div className="text-xs font-bold text-gray-700 line-clamp-1" title={exercise.notes}>{exercise.notes || "-"}</div>
                        <div className="text-[10px] font-bold text-orange-400 uppercase tracking-widest mt-0.5">Notes</div>
                    </div>
                </div>
                </div>

                <div className="mt-4 pt-4 border-t border-orange-100">
                     <button
                         onClick={handleLogToggle}
                         className={`w-full py-2 font-bold rounded-xl flex items-center justify-center gap-2 transition-colors ${logId ? "bg-red-50 text-red-600 hover:bg-red-100" : "bg-orange-50 text-orange-600 hover:bg-orange-100"}`}
                     >
                         {logId ? (
                            <>
                                <RotateCcw size={18} />
                                Unlog Cardio
                            </>
                         ) : (
                            <>
                                <CheckCircle size={18} />
                                Log Cardio
                            </>
                         )}
                     </button>
                   </div>
        </div>
    );
};

export default CardioCard;
