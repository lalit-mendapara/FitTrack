import React, { useState, useEffect } from 'react';
import { ArrowLeft, PlayCircle, HeartPulse, RefreshCw, MessageSquare, ChevronLeft } from 'lucide-react';
import ExerciseCard from './ExerciseCard';
import CardioCard from './CardioCard';
import { getDailyWorkoutLogs } from '../../api/tracking';

const ExerciseList = ({ dayPlan, onBack, onGenerate, onGenerateCustom, isGenerating, targetDate = null }) => {
  const [showCustomPromptModal, setShowCustomPromptModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState("");
  // const regenerateMenuRef = useRef(null); // Removed

  // Persistence: Fetch logs when this view mounts (similar to Page load)
  const [loggedExercises, setLoggedExercises] = useState([]);

  const fetchLogs = async () => {
      try {
          const dateToFetch = targetDate || new Date().toISOString().split('T')[0];
          const logs = await getDailyWorkoutLogs(dateToFetch);
          setLoggedExercises(logs.workouts || []);
      } catch (e) {
          console.error("Failed to fetch workout logs");
      }
  };

  useEffect(() => {
    fetchLogs();
  }, [targetDate]);



  const handleCustomGenerate = () => {
     onGenerateCustom(customPrompt);
     setShowCustomPromptModal(false);
  };

  return (
    <div className="container mx-auto px-6 py-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <button 
                onClick={onBack}
                className="p-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 text-gray-600 hover:text-gray-900 transition-all shadow-sm group"
            >
                <ChevronLeft size={20} className="group-hover:-translate-x-0.5 transition-transform" />
            </button>
            <div>
                <h2 className="text-3xl font-black text-gray-900 leading-none">{dayPlan.day_name}</h2>
                <div className="flex items-center gap-2 mt-2">
                    {dayPlan.primary_muscle_group && (
                        <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-100 uppercase tracking-wide">
                            {dayPlan.primary_muscle_group}
                        </span>
                    )}
                    <span className="text-xs font-bold text-gray-500 bg-gray-100 px-2.5 py-1 rounded-md border border-gray-200 uppercase tracking-wide">
                            {dayPlan.focus}
                    </span>
                </div>
            </div>
          </div>


      </div>

      <div className="space-y-8">
         {/* Main Workout List & Cardio Mixed */}
         <div>
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-indigo-100/50 text-indigo-600">
                    <PlayCircle size={20} className="fill-current bg-white rounded-full" />
                </div>
                <h3 className="text-lg font-extrabold text-gray-800 uppercase tracking-wide">Workout Routine</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Strength Exercises */}
                {dayPlan.exercises && (() => {
                    const muscleCounts = {};
                    return dayPlan.exercises.map((exercise, idx) => {
                        const foundLog = loggedExercises.find(l => l.name === exercise.exercise);
                        
                        // Calculate Sequence
                        const mGroup = exercise.target_muscle || "General";
                        if (!muscleCounts[mGroup]) muscleCounts[mGroup] = 0;
                        muscleCounts[mGroup]++;
                        
                        return (
                            <ExerciseCard 
                                key={`strength-${idx}`} 
                                exercise={exercise} 
                                initialLogId={foundLog?.id} 
                                targetDate={targetDate} 
                                onLogUpdate={fetchLogs}
                                muscleGroup={mGroup}
                                sequenceNumber={muscleCounts[mGroup]}
                            />
                        );
                    });
                })()}

                {/* Cardio Exercises - Merged into Grid */}
                {dayPlan.cardio_exercises && dayPlan.cardio_exercises.map((exercise, idx) => {
                    const foundLog = loggedExercises.find(l => l.name === exercise.exercise);
                    return <CardioCard key={`cardio-${idx}`} exercise={exercise} initialLogId={foundLog?.id} targetDate={targetDate} onLogUpdate={fetchLogs} />;
                })}
            </div>

            {/* Fallback for old string format (if no structured cardio) */}
            {(!dayPlan.cardio_exercises || dayPlan.cardio_exercises.length === 0) && dayPlan.cardio && (
                 <div className="mt-8 bg-white border border-orange-100 rounded-3xl p-6 md:p-8 shadow-sm">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 rounded-lg bg-orange-100 text-orange-600">
                            <HeartPulse size={24} />
                        </div>
                        <div>
                            <h3 className="text-xl font-black text-gray-900">Cardio Session</h3>
                        </div>
                    </div>
                    <p className="text-gray-700 font-medium text-lg leading-relaxed">
                        {typeof dayPlan.cardio === 'object' 
                            ? `${dayPlan.cardio.type || 'Cardio'} - ${dayPlan.cardio.duration_min || ''} mins` 
                            : dayPlan.cardio}
                    </p>
                 </div>
            )}
         </div>
      </div>

      {/* Custom Prompt Modal */}
      {showCustomPromptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-300">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h3 className="text-xl font-black text-gray-900">Customize Workout</h3>
              <button 
                onClick={() => setShowCustomPromptModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
              >
                X
              </button>
            </div>
            <div className="p-6">
                <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="E.g., 'Focus more on legs', 'Swap running for cycling'"
                className="w-full h-32 p-4 bg-gray-50 border border-gray-200 rounded-2xl text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 resize-none font-medium"
                autoFocus
                />
            </div>
            <div className="p-6 border-t border-gray-100 bg-gray-50/30 flex gap-3">
              <button
                onClick={handleCustomGenerate}
                disabled={isGenerating}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-200 transition-all transform active:scale-95"
              >
                {isGenerating ? <RefreshCw className="animate-spin" size={20}/> : <RefreshCw size={20}/>}
                Generate New Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExerciseList;
