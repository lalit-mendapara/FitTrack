import { Dumbbell, Repeat, Timer, Flame, CheckCircle, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';
import { logWorkout, deleteWorkoutLog } from '../../api/tracking';
import { toast } from 'react-toastify';
import { useState, useEffect } from 'react';

const ExerciseCard = ({ exercise, initialLogId = null, targetDate = null, onLogUpdate, muscleGroup, sequenceNumber }) => {
  // exercise object keys: exercise, sets, reps, rest_sec, image_url, instructions
  
  // State to track if logged locally (and store the ID)
  const [logId, setLogId] = useState(initialLogId);
  
  // Collapsible State for Mobile
  const [isExpanded, setIsExpanded] = useState(false);

  // Effect to handle initial screen size
  useEffect(() => {
    const handleResize = () => {
        if (window.innerWidth >= 768) { // md breakpoint
            setIsExpanded(true);
        } else {
            setIsExpanded(false);
        }
    };

    // Set initial
    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Sync if initialLogId changes (e.g. invalidation)
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
                    calories_burned: exercise.calories_burned,
                    sets: exercise.sets ? String(exercise.sets) : null,
                    reps: exercise.reps ? String(exercise.reps) : null,
                    muscle_group: exercise.muscle_group, // Note: backend property might be target_muscle now, but keeping as is if API expects this
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
    <div className="bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden hover:shadow-lg transition-all duration-300 flex flex-col h-full relative">
      
      {/* Exercise Image/Gif - Fixed Aspect Ratio/Height */}
      <div className="w-full h-64 bg-white flex items-center justify-center overflow-hidden border-b border-gray-50 relative group">
           {/* Calorie Badge */}
           {exercise.calories_burned > 0 && (
               <div className="absolute top-3 right-3 z-10">
                   <span className="px-2 py-1 bg-red-500 text-white text-[10px] font-black uppercase tracking-wider rounded-md shadow-sm flex items-center gap-1">
                       <Flame size={12} className="fill-current" />
                       {exercise.calories_burned} kcal
                   </span>
               </div>
           )}

           {/* Muscle Group Sequence Badge */}
           {muscleGroup && (
               <div className="absolute top-3 left-3 z-10">
                   <span className="px-2.5 py-1 bg-gray-900/80 backdrop-blur-sm text-white text-[10px] font-bold uppercase tracking-wider rounded-md shadow-sm border border-white/10">
                       {muscleGroup} #{sequenceNumber}
                   </span>
               </div>
           )}

           {exercise.image_url ? (
              <img 
                  src={exercise.image_url} 
                  alt={exercise.exercise} 
                  className="w-full h-full object-contain p-2 transition-transform duration-500 group-hover:scale-105"
              />
           ) : (
              <div className="text-gray-300">
                  <Dumbbell size={48} />
              </div>
           )}
      </div>

      {/* Details Content */}
      <div className="p-5 flex flex-col flex-1 relative">
           
          {/* Mobile Toggle Button */}
          <button 
                onClick={() => setIsExpanded(!isExpanded)}
                className="absolute top-5 right-5 p-1.5 rounded-full bg-gray-50 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors md:hidden z-20"
            >
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>

          <div className="flex justify-between items-start mb-3 pr-8 md:pr-0">
              <h3 className="text-xl font-black text-gray-900 leading-tight line-clamp-2">{exercise.exercise}</h3>
          </div>

          {/* Collapsible Instructions */}
          <div className={`transition-all duration-300 overflow-hidden ${isExpanded ? 'opacity-100 max-h-[500px] mb-4' : 'opacity-0 max-h-0 mb-0 md:opacity-100 md:max-h-[500px] md:mb-4'}`}>
              <div className="bg-indigo-50/50 rounded-xl p-3 border border-indigo-100/50">
                  {exercise.instructions ? (
                      Array.isArray(exercise.instructions) ? (
                        <ul className="space-y-2">
                            {exercise.instructions.map((point, idx) => (
                                <li key={idx} className="flex gap-2 text-xs text-gray-600 leading-relaxed font-medium">
                                    <span className="flex-shrink-0 w-1 h-1 rounded-full bg-indigo-400 mt-1.5"></span>
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
          </div>
          
          {/* Stats Grid - Always Visible */}
          <div className="grid grid-cols-3 gap-2 mt-auto">
              <div className="bg-indigo-50/50 rounded-xl p-2 py-3 text-center border border-indigo-50/50">
                  <div className="flex items-center justify-center text-indigo-500 mb-1">
                      <Repeat size={16} />
                  </div>
                  <div className="text-base font-bold text-gray-900">{exercise.sets}</div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wide">Sets</div>
              </div>
              <div className="bg-indigo-50/50 rounded-xl p-2 py-3 text-center border border-indigo-50/50">
                  <div className="flex items-center justify-center text-indigo-500 mb-1">
                      <Dumbbell size={16} />
                  </div>
                  <div className="text-base font-bold text-gray-900">{exercise.reps}</div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wide">Reps</div>
              </div>
              <div className="bg-indigo-50/50 rounded-xl p-2 py-3 text-center border border-indigo-50/50">
                  <div className="flex items-center justify-center text-indigo-500 mb-1">
                      <Timer size={16} />
                  </div>
                  <div className="text-base font-bold text-gray-900">{exercise.rest_sec}</div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wide">Rest</div>
              </div>
          </div>
          
           <div className="mt-4 pt-4 border-t border-gray-100">
             <button
                 onClick={handleLogToggle}
                 className={`w-full py-2 font-bold rounded-xl flex items-center justify-center gap-2 transition-colors ${logId ? "bg-red-50 text-red-600 hover:bg-red-100" : "bg-indigo-50 text-indigo-600 hover:bg-indigo-100"}`}
             >
                 {logId ? (
                    <>
                        <RotateCcw size={18} />
                        Unlog Set
                    </>
                 ) : (
                    <>
                        <CheckCircle size={18} />
                        Log Set
                    </>
                 )}
             </button>
           </div>
      </div>
    </div>
  );
};

export default ExerciseCard;

