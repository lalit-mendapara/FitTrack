import React, { useState, useRef } from 'react';
import Navbar from '../components/layout/Navbar';
import WorkoutDayCard from '../components/workout/WorkoutDayCard';
import ExerciseList from '../components/workout/ExerciseList';
import { Dumbbell, RefreshCw, MessageSquare, X, ChevronRight, AlertCircle, TrendingUp, HeartPulse, CheckCircle, Calendar } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWorkoutPlan } from '../hooks/useWorkoutPlan'; // Hook Import
import { Link, useSearchParams } from 'react-router-dom';
import GenerationOverlay from '../components/layout/GenerationOverlay';
import WorkoutSessionModal from '../components/workout/WorkoutSessionModal';
import { logWorkoutSession, deleteDailyWorkoutLogs, getDailyWorkoutLogs, deleteAllWorkoutLogs, checkWorkoutHistory } from '../api/tracking';
import { toast } from 'react-toastify';



const WORKOUT_GENERATION_STEPS = [
  "Generating workout plan",
  "Creating weekly schedule",
  "Assigning exercises per day",
  "Plan is created"
];

const WorkoutPlan = ({ isEmbedded = false }) => {
  const { user } = useAuth();
  
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [generationSuccess, setGenerationSuccess] = useState(false);
  const [loggedWorkouts, setLoggedWorkouts] = useState([]);
  const [hasSession, setHasSession] = useState(false);
  const [showConflictModal, setShowConflictModal] = useState(false);

  const onGenerateStart = () => {
    setShowGenerationModal(true);
    setLoadingStep(0);
    setGenerationSuccess(false);
  };

  const onGenerateEnd = () => {
      setGenerationSuccess(true);
      setLoadingStep(WORKOUT_GENERATION_STEPS.length - 1);
      
      setTimeout(() => {
          setShowGenerationModal(false);
          setGenerationSuccess(false);
          setLoadingStep(0);
      }, 2000);
  };

  const { 
    plan, 
    loading, 
    generating, 
    error, 
    showProfileUpdateWarning, 
    handleGenerate: generatePlan 
  } = useWorkoutPlan(onGenerateStart, onGenerateEnd);

  const [searchParams, setSearchParams] = useSearchParams();
  const activeDayKey = searchParams.get('day');


  
  // Derived state for view and selectedDay
  const selectedDay = (plan && activeDayKey && plan.weekly_schedule) ? plan.weekly_schedule[activeDayKey] : null;
  const view = selectedDay ? 'detail' : 'overview';

  // Helper: Calculate date for a specific day name (assuming current week)
  const getDateForDay = (dayName) => {
    if (!dayName) return new Date().toISOString().split('T')[0];
    
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const today = new Date();
    const currentDayIndex = today.getDay(); // 0-6 (Sun-Sat)
    
    // Simple normalization to handle case variations if any
    const targetDayIndex = days.findIndex(d => d.toLowerCase() === dayName.toLowerCase());
    
    if (targetDayIndex === -1) return today.toISOString().split('T')[0];
    
    // Calculate difference
    // Logic: We want the day within the "current" week window surrounding today?
    // Or strictly "This (past/coming) Monday"?
    // Standard interpretation: The Monday of *this week* (Sun-Sat or Mon-Sun).
    // Let's align with Mon-Sun ISO week for fitness apps usually.
    // If today is Wednesday, Monday is -2.
    // If today is Sunday, Monday was -6 (or +1 next week? usually past).
    
    // Robust approach: Difference from today.
    const diff = targetDayIndex - currentDayIndex;
    const targetDate = new Date(today);
    targetDate.setDate(today.getDate() + diff);
    
    return targetDate.toISOString().split('T')[0];
  };

  const targetDate = selectedDay ? getDateForDay(selectedDay.day_name || activeDayKey) : null;
  
  // Custom Prompt State
  const [showCustomPromptModal, setShowCustomPromptModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState("");
  const [showRegenerateOptions, setShowRegenerateOptions] = useState(false);
  const regenerateMenuRef = useRef(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (regenerateMenuRef.current && !regenerateMenuRef.current.contains(event.target)) {
        setShowRegenerateOptions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };

  }, []);

  // --- Reset Confirmation Logic ---
  const [showResetConfirmation, setShowResetConfirmation] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState(null);

  // State for persistence
  // Fetch logs on mount
  const fetchLogs = React.useCallback(async () => {
      try {
          const logs = await getDailyWorkoutLogs();
          setLoggedWorkouts(logs.workouts || []);
          setHasSession(logs.has_session || false);
      } catch (e) {
          console.error("Failed to fetch logs");
      }
  }, []);

  React.useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  React.useEffect(() => {
     console.log("DEBUG: Logged Workouts count:", loggedWorkouts.length);
     console.log("DEBUG: Has Session:", hasSession);
     console.log("DEBUG: Logged Workouts data:", loggedWorkouts);
  }, [loggedWorkouts, hasSession]);

  // Option 1: Clear Logs & Regenerate All
  const handleRegenerateFull = async () => {
      try {
          await deleteAllWorkoutLogs(); // Clear ALL logs and sessions
          setLoggedWorkouts([]); // Update local state immediately
          setHasSession(false);
          setShowConflictModal(false);
          setShowResetConfirmation(false); 
          toast.info("All logs cleared successfully");
          
          generatePlan(pendingPrompt, { ignore_history: true });
      } catch (e) {
          toast.error("Failed to clear logs. Please try again.");
      }
  };
  
  // Option 2: Keep Logs & Regenerate Others
  const handleRegeneratePartial = () => {
      setShowConflictModal(false);
      
      const loggedNames = loggedWorkouts.map(w => w.name).join(", ");
      const partialPrompt = `I have already completed these exercises today: ${loggedNames}. Please keep these entries in the schedule for today and only update the rest of the workout plan around them. ${pendingPrompt ? `Also: ${pendingPrompt}` : ""}`;
      
      generatePlan(partialPrompt);
  };

  // --- History Check Logic ---
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const handleGenerateClick = async (prompt = null) => {
      setShowCustomPromptModal(false);
      setPendingPrompt(prompt);
      
      // 1. Check for TODAY's logs (Immediate Conflict)
      if (loggedWorkouts.length > 0 || hasSession) {
          setShowConflictModal(true);
      } 
      // 2. Check for ANY history (User Request)
      else {
          try {
              const { has_history } = await checkWorkoutHistory();
              if (has_history) {
                  setShowHistoryModal(true);
              } else {
                  // No history, just generate
                  generatePlan(prompt);
              }
          } catch (e) {
              // Fallback if check fails
              generatePlan(prompt);
          }
      }
  };

  const handleClearHistoryAndRegenerate = async () => {
      try {
          await deleteAllWorkoutLogs(); 
          setLoggedWorkouts([]); 
          setHasSession(false);
          setShowHistoryModal(false);
          
          generatePlan(pendingPrompt, { ignore_history: true });
      } catch (e) {
          toast.error("Failed to clear logs.");
      }
  };

  const handleKeepHistoryAndRegenerate = () => {
      setShowHistoryModal(false);
      generatePlan(pendingPrompt);
  };
  const [startTime, setStartTime] = useState(null);
  const [sessionDuration, setSessionDuration] = useState(0);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [isSavingSession, setIsSavingSession] = useState(false);

  // Start timer when entering detail view
  React.useEffect(() => {
    if (view === 'detail') {
        // If we just entered detail view, set start time if not set
        if (!startTime) setStartTime(new Date());
    }
  }, [view, startTime]);

  const handleFinishWorkout = () => {
    if (!startTime) {
        setSessionDuration(45); // Default fallback
    } else {
        const now = new Date();
        const diffMs = now - startTime;
        const diffMins = Math.round(diffMs / 60000); // ms to min
        setSessionDuration(diffMins < 1 ? 1 : diffMins);
    }
    setIsSessionModalOpen(true);
  };

  const handleSaveSession = async (finalDuration) => {
      try {
          setIsSavingSession(true);
          const dateStr = targetDate || new Date().toISOString().split('T')[0];
          
          await logWorkoutSession({
              date: dateStr,
              duration_minutes: finalDuration
          });
          
          toast.success("Workout session saved!");
          setIsSessionModalOpen(false);
          // Optional: Navigate back or show summary?
          handleBack(); 
      } catch (error) {
          toast.error("Failed to save session.");
      } finally {
          setIsSavingSession(false);
      }
  };

  // Effect to cycle through loading steps
  React.useEffect(() => {
    let interval;
    if (showGenerationModal && !generationSuccess) {
      interval = setInterval(() => {
        setLoadingStep((prev) => {
           if (prev < WORKOUT_GENERATION_STEPS.length - 2) {
             return prev + 1;
           }
           return prev;
        });
      }, 6000); // Change message every 6s
    }
    return () => clearInterval(interval);
  }, [showGenerationModal, generationSuccess]);
  


  const [isCardioOpen, setIsCardioOpen] = useState(true);
  const [isProgressionOpen, setIsProgressionOpen] = useState(true);

  // Auto-collapse on mobile initially




  const handleSeeExercises = (dayKey) => {
    setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        newParams.set('day', dayKey);
        return newParams;
    });
  };

  const handleBack = () => {
    setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        newParams.delete('day');
        return newParams;
    });
  };

  if (loading) {
      return (
         <div className="min-h-screen bg-white flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
               <div className="animate-spin rounded-full h-12 w-12 border-[3px] border-gray-100 border-t-indigo-600"></div>
               <p className="text-indigo-600 font-medium animate-pulse">Loading Workout Plan...</p>
            </div>
         </div>
      );
  }

  return (
    <div className={`h-screen flex flex-col bg-gray-50/50 overflow-hidden`}>
      {!isEmbedded && <Navbar />}

      {showProfileUpdateWarning && (
        <div className="bg-amber-50 border-b border-amber-100 px-6 py-3">
          <div className="container mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="bg-amber-100 p-2 rounded-full text-amber-600">
                <RefreshCw size={18} />
              </div>
              <p className="text-amber-800 font-medium text-sm">
                You have updated your profile, so make sure you have regenerated your workout with new profile.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Hero / Header Section */}
      <div className={`${isEmbedded ? 'pt-4' : 'pt-20'} bg-white border-b border-gray-100 shadow-sm relative overflow-hidden mb-8 flex-shrink-0 z-10`}>
         <div className="absolute inset-0 bg-gradient-to-r from-indigo-50/50 to-white pointer-events-none"></div>
         <div className="container mx-auto px-6 relative z-10 pb-5">
            <div className="flex flex-col lg:flex-row justify-between items-center gap-4">
                <div className="text-center lg:text-left">
                    <h1 className="text-3xl font-black text-gray-900 tracking-tight mb-1 flex items-center justify-center lg:justify-start gap-3">
                      <div className="p-2 bg-indigo-100 rounded-lg text-indigo-600">
                        <Dumbbell size={24} />
                      </div>
                      Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">Workout Plan</span>
                    </h1>
                    {plan && (
                        <div className="flex flex-col items-center lg:items-start gap-2 mt-2">
                             <p className="text-sm text-gray-500 font-medium max-w-sm mx-auto lg:mx-0">
                                {plan.plan_name || "Personalized Plan"} • {plan.duration_weeks || 8} Weeks
                             </p>
                             {plan.primary_goal && (
                                <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-extrabold uppercase tracking-wider rounded-full border border-indigo-100 shadow-sm">
                                    {plan.primary_goal.replace(/_/g, " ")}
                                </span>
                             )}
                        </div>
                    )}
                </div>
            </div>
         </div>
      </div>

      <div className={`flex-1 overflow-y-auto no-scrollbar ${isEmbedded ? '' : 'pb-24'}`}>
        <div className="container mx-auto px-6">
        {!plan ? (
             <div className="text-center py-20">
               <div className="max-w-lg mx-auto bg-white p-12 rounded-[2rem] shadow-xl border border-gray-100">
                  <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-8 animate-bounce-slow">
                     <Dumbbell size={40} className="text-indigo-600" />
                  </div>
                  <h2 className="text-4xl font-black text-gray-900 mb-4">Ready to Train?</h2>
                  <p className="text-gray-600 mb-10 text-xl font-medium">Generate your personalized AI workout plan based on your preferences.</p>
                  <button 
                     onClick={() => handleGenerateClick(null)}
                     disabled={generating}
                     className={`w-full py-5 bg-indigo-600 text-white font-bold text-xl rounded-2xl shadow-lg hover:shadow-xl hover:bg-indigo-700 transition-all transform hover:-translate-y-1 flex items-center justify-center gap-3 ${generating ? 'opacity-70 cursor-wait' : ''}`}
                  >
                     {generating ? (
                       <>
                         <RefreshCw className="animate-spin" /> Generating...
                       </>
                     ) : (
                       'Generate Plan'
                     )}
                  </button>
               </div>
            </div>
        ) : (
            view === 'overview' ? (
                <>
                {/* Cardio & Progression - 2 Column Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
                   {/* Cardio Card */}
                   <div className="bg-white p-6 rounded-2xl shadow-sm border border-orange-100 relative overflow-hidden group hover:shadow-md transition-all">
                      <div className="absolute top-0 right-0 w-32 h-32 bg-orange-50 rounded-bl-[100px] -mr-10 -mt-10 transition-transform group-hover:scale-110"></div>
                      <div className="relative z-10">
                         <div 
                            className="flex items-center justify-between mb-4 cursor-pointer md:cursor-default"
                            onClick={() => setIsCardioOpen(!isCardioOpen)}
                         >
                             <div className="flex items-center gap-3">
                                <div className="p-2 bg-orange-100 text-orange-600 rounded-lg">
                                   <HeartPulse size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900">Cardio Recommendations</h3>
                             </div>
                             <div className={`md:hidden transform transition-transform duration-300 ${isCardioOpen ? 'rotate-180' : ''}`}>
                                <ChevronRight size={20} className="text-gray-400 rotate-90" />
                             </div>
                         </div>
                         
                         <div className={`transition-all duration-300 overflow-hidden md:max-h-[800px] md:opacity-100 md:mt-2 ${isCardioOpen ? 'max-h-[800px] opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                             <ul className="space-y-3">
                                {plan.cardio_recommendations && plan.cardio_recommendations.length > 0 ? (
                                    plan.cardio_recommendations.map((item, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-gray-600 text-sm font-medium">
                                            <div className="w-1.5 h-1.5 rounded-full bg-orange-400 mt-1.5 flex-shrink-0"></div>
                                            <span>{item}</span>
                                        </li>
                                    ))
                                ) : (
                                    <p className="text-gray-400 text-sm italic">No specific cardio recommendations.</p>
                                )}
                             </ul>
                         </div>
                      </div>
                   </div>

                   {/* Progression Card */}
                   <div className="bg-white p-6 rounded-2xl shadow-sm border border-indigo-100 relative overflow-hidden group hover:shadow-md transition-all">
                      <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-bl-[100px] -mr-10 -mt-10 transition-transform group-hover:scale-110"></div>
                       <div className="relative z-10">
                         <div 
                            className="flex items-center justify-between mb-4 cursor-pointer md:cursor-default"
                            onClick={() => setIsProgressionOpen(!isProgressionOpen)}
                         >
                             <div className="flex items-center gap-3">
                                <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                                   <TrendingUp size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900">Progression Guidelines</h3>
                             </div>
                             <div className={`md:hidden transform transition-transform duration-300 ${isProgressionOpen ? 'rotate-180' : ''}`}>
                                <ChevronRight size={20} className="text-gray-400 rotate-90" />
                             </div>
                         </div>
                         
                         <div className={`transition-all duration-300 overflow-hidden md:max-h-[800px] md:opacity-100 md:mt-2 ${isProgressionOpen ? 'max-h-[800px] opacity-100 mt-2' : 'max-h-0 opacity-0'}`}>
                             <ul className="space-y-3">
                                {plan.progression_guidelines && plan.progression_guidelines.length > 0 ? (
                                    plan.progression_guidelines.map((item, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-gray-600 text-sm font-medium">
                                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0"></div>
                                            <span>{item}</span>
                                        </li>
                                    ))
                                ) : (
                                    <p className="text-gray-400 text-sm italic">Follow standard progressive overload.</p>
                                )}
                             </ul>
                         </div>
                       </div>
                   </div>
                </div>

                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 px-1">
                   <div className="flex flex-wrap items-center gap-3">
                       <h2 className="text-2xl font-black text-gray-800 tracking-tight">Weekly Schedule</h2>
                       {/* Date Duration Badge */}
                       <div className="px-3 py-1 bg-gray-100 rounded-lg border border-gray-200 text-xs font-semibold text-gray-600 flex items-center gap-1.5">
                           <Calendar size={12} className="text-gray-500" />
                           <span>
                               {(() => {
                                   // Calculate start and end of week (Sunday to Saturday based on getDateForDay logic)
                                   const start = new Date(getDateForDay('Sunday'));
                                   const end = new Date(getDateForDay('Saturday'));
                                   const options = { month: 'short', day: 'numeric' };
                                   return `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
                               })()}
                           </span>
                       </div>
                       {/* Fitness Goal Badge - Beside Heading */}
                       {plan.primary_goal && (
                           <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold uppercase tracking-wide rounded-full border border-indigo-100 flex items-center gap-1">
                               <span className="opacity-70">Goal:</span>
                               <span>{plan.primary_goal.replace(/_/g, " ")}</span>
                           </span>
                       )}
                   </div>
                   <div className="relative w-full md:w-auto flex justify-end" ref={regenerateMenuRef}>
                        <button 
                             onClick={() => setShowRegenerateOptions(!showRegenerateOptions)}
                             disabled={generating}
                             className="flex items-center gap-2 px-3 py-2 md:px-5 md:py-2.5 bg-white rounded-xl shadow-sm border border-gray-100 text-indigo-600 font-bold text-xs md:text-sm hover:bg-indigo-50 transition-colors"
                        >
                             <RefreshCw className={`w-4 h-4 md:w-[18px] md:h-[18px] ${generating ? "animate-spin" : ""}`} />
                             {generating ? 'Updating...' : 'Regenerate'}
                        </button>

                        {/* Regenerate Dropdown */}
                        {showRegenerateOptions && !generating && (
                            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-20 animate-in fade-in slide-in-from-top-2 duration-200">
                                <button
                                    onClick={() => {
                                        setShowRegenerateOptions(false);
                                        handleGenerateClick(null);
                                    }}
                                    className="w-full text-left px-4 py-3 text-sm font-medium text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 flex items-center gap-2 transition-colors border-b border-gray-50"
                                >
                                    <RefreshCw size={16} />
                                    Regenerate
                                </button>
                                <button
                                    onClick={() => {
                                        setShowRegenerateOptions(false);
                                        setCustomPrompt(""); // Clear the textarea
                                        setShowCustomPromptModal(true);
                                    }}
                                    className="w-full text-left px-4 py-3 text-sm font-medium text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 flex items-center gap-2 transition-colors"
                                >
                                    <MessageSquare size={16} />
                                    Suggestion
                                </button>
                            </div>
                        )}
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
                  {plan.weekly_schedule && Object.entries(plan.weekly_schedule).map(([key, day]) => (
                    <WorkoutDayCard 
                        key={key} 
                        dayPlan={day} 
                        date={getDateForDay(day.day_name)}
                        onSeeExercises={() => handleSeeExercises(key)} 
                    />
                  ))}
                  {!plan.weekly_schedule && (
                      <div className="col-span-full text-center text-gray-500 py-10">
                          No schedule data found. Please regenerate.
                      </div>
                  )}
                </div>
                </>
            ) : (
                <div className="pb-24"> {/* Add padding for fixed bottom bar if needed, or just flow */}
                    <ExerciseList 
                        dayPlan={selectedDay} 
                        onBack={handleBack}
                        onGenerate={() => handleGenerateClick(null)}
                        onGenerateCustom={(prompt) => handleGenerateClick(prompt)}
                        isGenerating={generating}
                        targetDate={targetDate}
                    />
                    
                    {/* Finish Workout Floating Button (or Static at bottom) */}
                    <div className="mt-8 flex justify-center">
                        <button
                            onClick={handleFinishWorkout}
                            className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-black text-lg rounded-2xl shadow-xl shadow-emerald-200 transform transition-all hover:-translate-y-1 active:scale-95 flex items-center justify-center gap-3"
                        >
                            <CheckCircle size={24} className="animate-pulse" />
                            Finish Workout
                        </button>
                    </div>
                </div>
            )
        )}
      </div>
      </div>

      <WorkoutSessionModal 
        isOpen={isSessionModalOpen}
        onClose={() => setIsSessionModalOpen(false)}
        initialDuration={sessionDuration}
        onSave={handleSaveSession}
        isSaving={isSavingSession}
      />


      {/* Custom Prompt Modal */}
      {showCustomPromptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-300">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 text-indigo-600 rounded-xl">
                  <MessageSquare size={20} />
                </div>
                <h3 className="text-xl font-black text-gray-900">Customize Workout</h3>
              </div>
              <button 
                onClick={() => setShowCustomPromptModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              <p className="text-gray-600 text-sm font-medium mb-4">
                Want to adjust your routine? Tell our AI coach what to change.
              </p>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="E.g., 'Focus more on legs', 'I have a shoulder injury, avoid overhead press', 'Swap running for cycling'"
                className="w-full h-32 p-4 bg-gray-50 border border-gray-200 rounded-2xl text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none transition-all"
                autoFocus
              />
            </div>

            <div className="p-6 border-t border-gray-100 bg-gray-50/30 flex gap-3">
              <button
                onClick={() => handleGenerateClick(customPrompt)}
                disabled={generating}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 transition-all transform active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generating ? <RefreshCw className="animate-spin" size={20}/> : <RefreshCw size={20}/>}
                {generating ? 'Regenerating...' : 'Generate New Plan'}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* History Check Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
           <div className="bg-white rounded-[2rem] p-8 shadow-2xl max-w-md w-full border border-gray-100 relative overflow-hidden">
               <div className="text-center mb-6">
                   <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-4 text-indigo-500">
                      <RefreshCw size={32} />
                   </div>
                   <h3 className="text-2xl font-black text-gray-900 mb-2">Existing Workout History</h3>
                   <p className="text-gray-500">
                     We found previous workout logs. How would you like to proceed with the new plan?
                   </p>
               </div>
               
               <div className="space-y-3">
                   <button 
                      onClick={handleClearHistoryAndRegenerate}
                      disabled={generating}
                      className="w-full py-3.5 bg-red-50 text-red-600 font-bold rounded-xl hover:bg-red-100 border border-red-100 shadow-sm transition-all transform active:scale-95 flex items-center justify-center gap-2"
                   >
                      <RefreshCw size={18} />
                      {generating ? 'Regenerating...' : 'Clear History & Start Fresh'}
                   </button>
                   
                   <button 
                      onClick={handleKeepHistoryAndRegenerate}
                      disabled={generating}
                      className="w-full py-3.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all transform active:scale-95 flex items-center justify-center gap-2"
                   >
                      <CheckCircle size={18} />
                      {generating ? 'Regenerating...' : 'Keep History & Update Plan'}
                   </button>
                   
                   <button 
                      onClick={() => setShowHistoryModal(false)}
                      disabled={generating}
                      className="w-full py-3.5 text-gray-500 font-bold hover:text-gray-700 transition-colors"
                   >
                      Cancel
                   </button>
               </div>
           </div>
        </div>
      )}
      {/* Conflict Modal */}
      {showConflictModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
           <div className="bg-white rounded-[2rem] p-8 shadow-2xl max-w-md w-full border border-gray-100 relative overflow-hidden">
               <div className="text-center mb-6">
                   <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4 text-amber-500">
                      <RefreshCw size={32} />
                   </div>
                   <h3 className="text-2xl font-black text-gray-900 mb-2">Existing Logs Found</h3>
                   <p className="text-gray-500">
                     You have already logged workouts for today. Regenerating the plan might cause inconsistencies.
                   </p>
               </div>
               
               <div className="space-y-3">
                   <button 
                      onClick={handleRegenerateFull}
                      disabled={generating}
                      className="w-full py-3.5 bg-red-50 text-red-600 font-bold rounded-xl hover:bg-red-100 transition-colors flex items-center justify-center gap-2 border border-red-100"
                   >
                      <RefreshCw size={18} />
                      {generating ? 'Clearing & Regenerating...' : 'Clear Logs & Regenerate All'}
                   </button>
                   
                   <button 
                      onClick={handleRegeneratePartial}
                      disabled={generating}
                      className="w-full py-3.5 bg-indigo-50 text-indigo-600 font-bold rounded-xl hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2 border border-indigo-100"
                   >
                      <CheckCircle size={18} />
                      {generating ? 'Regenerating...' : 'Keep Logs & Regenerate Others'}
                   </button>
                   
                   <button 
                      onClick={() => setShowConflictModal(false)}
                      disabled={generating}
                      className="w-full py-3.5 text-gray-500 font-bold hover:text-gray-700 transition-colors"
                   >
                      Cancel
                   </button>
               </div>
           </div>
        </div>
      )}

      {/* Generation Loading / Success Modal */}
      <GenerationOverlay 
        isVisible={showGenerationModal}
        steps={WORKOUT_GENERATION_STEPS}
        currentStepIndex={loadingStep}
        isSuccess={generationSuccess}
        title="Building Plan"
        successTitle="All Set!"
        type="workout"
      />
    </div>
  );
};

export default WorkoutPlan;
