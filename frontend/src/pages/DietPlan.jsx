
import React, { useState, useRef } from 'react';
import Navbar from '../components/layout/Navbar';
import { Link } from 'react-router-dom';
import GenerationOverlay from '../components/layout/GenerationOverlay';
import { useDietPlan } from '../hooks/useDietPlan'; // Hook Import
import { useAuth } from '../context/AuthContext';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { Calendar, Apple, Coffee, Moon, Sun, ChevronRight, RefreshCw, X, MessageSquare,BicepsFlexed,LeafyGreen,PersonStanding, Zap, CheckCircle, RotateCcw } from 'lucide-react';
import { logMeal, deleteMealLog, getDailyDietLogs, deleteDailyDietLogs } from '../api/tracking';
import { toast } from 'react-toastify';
import MealCard from '../components/dashboard/MealCard';

// CONSTANTS REMOVED (Moved to MealCard or unused)



const GENERATION_STEPS = [
  "Generating diet plan",
  "Creating breakfast", 
  "Creating lunch",
  "Creating dinner",
  "Creating snack",
  "Plan is created" 
];

const DietPlan = ({ isEmbedded = false }) => {
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [generationSuccess, setGenerationSuccess] = useState(false);

  const onGenerateStart = () => {
    setShowGenerationModal(true);
    setLoadingStep(0);
    setGenerationSuccess(false);
  };

  const onGenerateEnd = () => {
      // Start success sequence
      setGenerationSuccess(true);
      setLoadingStep(GENERATION_STEPS.length - 1); // Set to last step (Success message)
      
      // Close after delay
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
    handleGenerate: generatePlan,
    handleRegenerate,
    isPlanExpired
  } = useDietPlan(onGenerateStart, onGenerateEnd);

  const [showCustomPromptModal, setShowCustomPromptModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState("");
  const [showRegenerateOptions, setShowRegenerateOptions] = useState(false);
  const [showConflictModal, setShowConflictModal] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState(null);
  
  const regenerateMenuRef = useRef(null);

  // State for persistence
  const [loggedMeals, setLoggedMeals] = useState([]);

  // Fetch logs on mount
  const fetchLogs = React.useCallback(async () => {
      try {
          const logs = await getDailyDietLogs();
          setLoggedMeals(logs.meals);
      } catch (e) {
          console.error("Failed to fetch logs");
      }
  }, []);

  React.useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Handle Generate Click with Pre-Check
  const handleGenerateClick = (prompt = null) => {
     setShowCustomPromptModal(false);
     
     // Check for existing logs
     if (loggedMeals.length > 0) {
         setPendingPrompt(prompt);
         setShowConflictModal(true);
     } else {
         generatePlan(prompt);
     }
  };

  // Option 1: Clear Logs & Regenerate All
  const handleRegenerateFull = async () => {
      try {
          await deleteDailyDietLogs(); // Clear logs
          setLoggedMeals([]); // Update local state immediately
          setShowConflictModal(false);
          toast.info("Logs cleared successfully");
          
          generatePlan(pendingPrompt);
      } catch (e) {
          toast.error("Failed to clear logs. Please try again.");
      }
  };
  
  // Option 2: Keep Logs & Regenerate Others
  const handleRegeneratePartial = () => {
      setShowConflictModal(false);
      
      // Construct a partial regeneration prompt
      // Identify unlogged meals
      // Note: This logic depends on backend supporting this nuance or us crafting a prompt
      // Since our goal is simple, let's just create a prompt that says:
      // "Regenerate the plan but KEEP the meals that are similar to: [Logged Meal Names]. Only change other meals."
      // OR better, just tell LLM "I have already eaten [X], please generate rest of the day around it."
      
      const loggedNames = loggedMeals.map(m => m.name).join(", ");
      const partialPrompt = `I have already logged/eaten: ${loggedNames}. Please keep these meals or similar items in the plan unchanged if possible, and regenerate the rest of the plan to balance nutrition around them. ${pendingPrompt ? `Also: ${pendingPrompt}` : ""}`;
      
      generatePlan(partialPrompt);
  };


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

  // Effect to cycle through loading steps
  React.useEffect(() => {
    let interval;
    if (showGenerationModal && !generationSuccess) {
      interval = setInterval(() => {
        setLoadingStep((prev) => {
           // Cycle up to second-to-last step (before "Plan is created")
           if (prev < GENERATION_STEPS.length - 2) {
             return prev + 1;
           }
           return prev;
        });
      }, 6000); // Change message every 3s
    }
    return () => clearInterval(interval);
  }, [showGenerationModal, generationSuccess]);


  const NutrientMeter = ({ value, label, unit, color, icon: Icon, total = 100 }) => {
    const data = [
      { value: value, fill: color },
      { value: total > value ? total - value : 0, fill: '#f3f4f6' }
    ];
    
    return (
      <div className="flex flex-col items-center group ">
       <div className="relative w-16 h-16 sm:w-20 sm:h-20">
           <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <PieChart>
              <Pie
                data={[{ value: 100 }]} 
                cx="50%"
                cy="50%"
                innerRadius="70%"
                outerRadius="90%"
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                stroke="none"
              >
                  <Cell fill={color} className="opacity-20 translate-y-2"/>
              </Pie>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius="70%"
                outerRadius="90%"
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                cornerRadius={10}
                stroke="none"
              >
                <Cell fill={color} />
                <Cell fill="#f3f4f6" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center text-gray-400 group-hover:scale-110 transition-transform duration-300">
             <Icon size={20} style={{ color: color }} />
          </div>
        </div>
        <div className="text-center mt-1.5">
            <p className="text-lg font-extrabold text-gray-800 tabular-nums leading-none">
                {Number(value).toFixed(0)}<span className="text-[10px] text-gray-400 ml-0.5 font-bold">{unit}</span>
            </p>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mt-0.5">{label}</p>
        </div>
      </div>
    );
  };

  const MacroChart = ({ protein, carbs, fat }) => {
    const data = [
      { name: 'Protein', value: protein },
      { name: 'Carbs', value: carbs },
      { name: 'Fat', value: fat },
    ];

    return (
      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={38}
              outerRadius={55}
              paddingAngle={5}
              dataKey="value"
              cornerRadius={4}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <RechartsTooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px', fontWeight: 600 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  };



  if (loading) {
     return (
        <div className="min-h-screen bg-white flex items-center justify-center">
           <div className="flex flex-col items-center gap-4">
              <div className="animate-spin rounded-full h-12 w-12 border-[3px] border-gray-100 border-t-indigo-600"></div>
              <p className="text-indigo-600 font-medium animate-pulse">Loading Plan...</p>
           </div>
        </div>
     );
  }

  if (error === "PROFILE_MISSING") {
      return (
        <div className="min-h-screen bg-gray-50/50">
           {!isEmbedded && <Navbar />}
           <div className={`${isEmbedded ? '' : 'pt-24'} container mx-auto px-6 text-center`}>
              <div className="max-w-md mx-auto bg-white p-8 rounded-3xl shadow-[0_20px_50px_-12px_rgba(0,0,0,0.1)] border border-gray-100">
                 <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-6 text-red-500">
                    <Apple size={32} />
                 </div>
                 <h2 className="text-2xl font-bold text-gray-900 mb-2">Profile Incomplete</h2>
                 <p className="text-gray-500 mb-8">Please complete your physical profile to generate your personalized diet plan.</p>
                 <Link to="/profile" className="inline-flex items-center justify-center px-8 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-all hover:shadow-lg hover:-translate-y-0.5">
                    Go to Profile <ChevronRight size={18} className="ml-2" />
                 </Link>
              </div>
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
                You have updated your profile, so make sure you have regenerated your diet with new profile.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Hero / Header Section */}
      <div className={`${isEmbedded ? 'pt-4' : 'pt-20'} bg-white border-b border-gray-100 shadow-sm relative overflow-hidden flex-shrink-0 z-10`}>
         <div className="absolute inset-0 bg-gradient-to-r from-indigo-50/50 to-white pointer-events-none"></div>
         <div className="container mx-auto px-6 relative z-10 pb-5">
            <div className="flex flex-col lg:flex-row justify-between items-center gap-4">
               <div className="text-center lg:text-left">
                  <h1 className="text-3xl font-black text-gray-900 tracking-tight mb-1">
                    Your Daily <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-indigo-400">Nutrition</span>
                  </h1>
                  <p className="text-sm text-gray-500 font-medium max-w-sm mx-auto lg:mx-0">
                    Your personalized plan designed to help you achieve your goal efficiently.
                  </p>
               </div>
               
               {/* Meters Section */}
               {plan && (
                 <div className="flex flex-wrap justify-center gap-3 sm:gap-6">
                     <NutrientMeter 
                        value={plan.daily_generated_totals?.calories || 0} 
                        label="Calories" 
                        unit="" 
                        color="#6366f1" 
                        icon={Zap}
                        total={2500}
                     />
                     <NutrientMeter 
                        value={plan.daily_generated_totals?.protein || 0} 
                        label="Protein" 
                        unit="g" 
                        color="#818cf8"
                        icon={BicepsFlexed}
                        total={200}
                     />
                     <NutrientMeter 
                        value={plan.daily_generated_totals?.carbs || 0} 
                        label="Carbs" 
                        unit="g" 
                        color="#34d399"
                        icon={LeafyGreen}
                        total={300}
                     />
                     <NutrientMeter 
                        value={plan.daily_generated_totals?.fat || 0} 
                        label="Fat" 
                        unit="g" 
                        color="#f472b6"
                        icon={PersonStanding}
                        total={100}
                     />
                 </div>
               )}
            </div>
         </div>
      </div>

      <div className={`flex-1 overflow-y-auto no-scrollbar ${isEmbedded ? '' : 'pb-24'}`}>
        <div className="container mx-auto px-6 mt-6">
         {!plan || isPlanExpired ? (
            <div className="text-center py-20">
               <div className="max-w-lg mx-auto bg-white p-12 rounded-[2rem] shadow-xl border border-gray-100">
                  <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-8 animate-bounce-slow">
                     <RefreshCw size={40} className="text-indigo-600" />
                  </div>
                  {isPlanExpired && plan ? (
                      <>
                        <h2 className="text-4xl font-black text-gray-900 mb-4">Good Morning!</h2>
                        <p className="text-gray-600 mb-2 text-xl font-medium">
                            Your diet plan will be auto generated by 5 am.
                        </p>
                        <p className="text-gray-500 mb-10 text-sm">
                            If you want to generate now, you can generate manually.
                        </p>
                        <button 
                           onClick={() => handleRegenerate()}
                           disabled={generating}
                           className={`w-full py-5 bg-indigo-600 text-white font-bold text-xl rounded-2xl shadow-lg hover:shadow-xl hover:bg-indigo-700 transition-all transform hover:-translate-y-1 flex items-center justify-center gap-3 ${generating ? 'opacity-70 cursor-wait' : ''}`}
                        >
                           {generating ? (
                             <>
                               <RefreshCw className="animate-spin" /> Generating...
                             </>
                           ) : (
                             'Generate Plan Now'
                           )}
                        </button>
                      </>
                  ) : (
                      <>
                          <h2 className="text-4xl font-black text-gray-900 mb-4">Ready to Start?</h2>
                          <p className="text-gray-600 mb-10 text-xl font-medium">Generate your personalized AI diet plan in seconds.</p>
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
                      </>
                  )}
               </div>
            </div>
         ) : (
            <>
               <div className="flex justify-between items-center mb-6 px-1">
                   <h2 className="text-2xl font-black text-gray-800 tracking-tight">Today's Meals</h2>
                   <div className="relative" ref={regenerateMenuRef}>
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
               
               <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 gap-6 pb-12">
                  {plan.meal_plan?.map((meal) => (
                     <MealCard 
                        key={meal.meal_id} 
                        meal={meal} 
                        loggedMeals={loggedMeals}
                        onLogUpdate={fetchLogs}
                     />
                  ))}
               </div>
            </>
         )}
      </div>
      </div>

      {/* Custom Prompt Modal */}
      {showCustomPromptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-300">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 text-indigo-600 rounded-xl">
                  <MessageSquare size={20} />
                </div>
                <h3 className="text-xl font-black text-gray-900">How can I help you?</h3>
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
                Have specific preferences? Let our AI know what you'd like to change or focus on.
              </p>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="E.g., 'I prefer more vegetarian options for lunch', 'No mushrooms please', 'High protein breakfast'"
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
                {generating ? 'Generating...' : 'Generate New Plan'}
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
                     You have already logged meals for today. Regenerating the plan might cause inconsistencies.
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
        steps={GENERATION_STEPS}
        currentStepIndex={loadingStep}
        isSuccess={generationSuccess}
        title="Please Wait"
        successTitle="All Set!"
        type="diet"
      />
    </div>
  );
};

export default DietPlan;
