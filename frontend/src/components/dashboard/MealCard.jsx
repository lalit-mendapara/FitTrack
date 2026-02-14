import React, { useState, useEffect } from 'react';
import { Sun, Calendar, Moon, Coffee, Apple, CheckCircle, RotateCcw, ChevronDown, ChevronUp, SkipForward } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { toast } from 'react-toastify';
import { logMeal, deleteMealLog } from '../../api/tracking';
import { skipMeal } from '../../api/socialEventService';

const COLORS = ['#818cf8', '#34d399', '#f472b6']; // Indigo, Emerald, Pink

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

const MealCard = ({ meal, loggedMeals, onLogUpdate, socialEvent, onPlanRefresh }) => {
    const icons = {
      breakfast: Sun,
      lunch: Calendar,
      dinner: Moon,
      snack: Coffee
    };
    const Icon = icons[meal.meal_id] || Apple;
    
    // State to track if logged locally
    const initialLogId = loggedMeals.find(l => l.name === meal.dish_name)?.id || null;
    const [logId, setLogId] = useState(initialLogId);
    
    // Collapsible State (Default expanded on large screens, collapsed on small)
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
    
    // Sync if initialLogId changes
    useEffect(() => {
        setLogId(initialLogId);
    }, [initialLogId]);

    const handleLogToggle = async (e) => {
        e.stopPropagation(); // Prevent toggling accordion when clicking log button
        try {
            if (logId) {
                // UNLOG
                await deleteMealLog(logId);
                setLogId(null);
                onLogUpdate(); 
                toast.info(`Unlogged ${meal.dish_name}`);
            } else {
                // LOG
                const calories = (meal.nutrients.p * 4) + (meal.nutrients.c * 4) + (meal.nutrients.f * 9);
                
                const mealTypeMap = {
                  breakfast: 'Breakfast',
                  lunch: 'Lunch',
                  dinner: 'Dinner',
                  snack: 'Snack'
                };
                
                const res = await logMeal({
                    meal_name: meal.dish_name,
                    meal_type: mealTypeMap[meal.meal_id] || 'Snack',
                    calories: calories,
                    protein: meal.nutrients.p,
                    carbs: meal.nutrients.c,
                    fat: meal.nutrients.f,
                    date: new Date().toISOString().split('T')[0]
                });
                setLogId(res.log_id);
                onLogUpdate(); 
                toast.success(`Logged ${meal.dish_name}!`);
            }
        } catch (e) {
            toast.error("Failed to update log.");
        }
    };

    const [skipping, setSkipping] = useState(false);
    
    const handleSkipMeal = async (e) => {
        e.stopPropagation();
        const isFeastDay = socialEvent?.status === 'FEAST_DAY';
        const confirmMsg = isFeastDay
            ? `Skip ${meal.label}? Its calories will be redistributed to your other meals.`
            : `Skip ${meal.label}? Its calories will be banked for your feast day.`;
        if (!window.confirm(confirmMsg)) return;
        
        setSkipping(true);
        try {
            await skipMeal(meal.meal_id, null, isFeastDay);
            toast.success(isFeastDay
                ? `Skipped ${meal.label}! Calories redistributed.`
                : `Skipped ${meal.label}! Calories banked 🏦`
            );
            if (onPlanRefresh) onPlanRefresh();
        } catch (err) {
            toast.error('Failed to skip meal.');
        } finally {
            setSkipping(false);
        }
    };
    
    return (
      <div className="bg-white rounded-[2rem] shadow-lg border border-gray-100/50 overflow-hidden hover:shadow-2xl hover:border-indigo-100 transition-all duration-300 group h-full flex flex-col">
        <div className="p-6 flex-1 flex flex-col relative">
            {/* Toggle Button for Mobile */}
            <button 
                onClick={() => setIsExpanded(!isExpanded)}
                className="absolute top-6 right-6 p-2 rounded-full bg-gray-50 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors md:hidden"
            >
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>

          <div className="flex justify-between items-start mb-4 pr-10 md:pr-0">
             <div className="flex items-center gap-4">
                <div className="p-3 bg-indigo-50/80 rounded-2xl text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300 shrink-0">
                  <Icon size={28} strokeWidth={2.5} />
                </div>
                <div>
                   <h3 className="text-2xl font-black text-gray-900 capitalize leading-none mb-1">{meal.label}</h3>
                   <span className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide ${meal.is_veg ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {meal.is_veg ? 'Veg' : 'Non-Veg'}
                   </span>
                   {meal.is_user_adjusted && (
                       <span className="text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide bg-blue-100 text-blue-700 ml-2">
                           Adjusted
                       </span>
                   )}
                </div>
             </div>
             {/* Desktop Calories Display */}
             <div className="text-right hidden md:block">
                {meal.original_nutrients ? (
                    <div className="flex flex-col items-end">
                        <span className="text-xs text-gray-400 line-through decoration-red-400 decoration-2">
                             {Number((meal.original_nutrients.p * 4) + (meal.original_nutrients.c * 4) + (meal.original_nutrients.f * 9)).toFixed(0)}
                        </span>
                        <span className="text-2xl font-black text-purple-600 block">
                            {Number((meal.nutrients.p * 4) + (meal.nutrients.c * 4) + (meal.nutrients.f * 9)).toFixed(0)}
                        </span>
                        <span className="text-[10px] font-bold text-purple-600 px-1.5 rounded bg-purple-100 uppercase tracking-wide">
                            Feast Mode
                        </span>
                    </div>
                ) : (
                    <>
                        <span className="text-2xl font-black text-indigo-600 block">{Number((meal.nutrients.p * 4) + (meal.nutrients.c * 4) + (meal.nutrients.f * 9)).toFixed(0)}</span>
                        <span className="text-xs text-gray-400 uppercase font-bold tracking-wider">Kcal</span>
                    </>
                )}
             </div>
          </div>

          <div className="mb-5">
             {/* Mobile Calories Row */}
            <div className="flex md:hidden items-baseline gap-2 mb-2">
                 {meal.original_nutrients ? (
                    <>
                         <span className="text-sm text-gray-400 line-through decoration-red-400 decoration-2">
                             {Number((meal.original_nutrients.p * 4) + (meal.original_nutrients.c * 4) + (meal.original_nutrients.f * 9)).toFixed(0)}
                        </span>
                        <span className="text-2xl font-black text-purple-600">
                            {Number((meal.nutrients.p * 4) + (meal.nutrients.c * 4) + (meal.nutrients.f * 9)).toFixed(0)}
                        </span>
                        <span className="text-[10px] font-bold text-purple-600 px-1.5 rounded bg-purple-100 uppercase tracking-wide">
                            Feast
                        </span>
                    </>
                 ) : (
                    <>
                        <span className="text-2xl font-black text-indigo-600">{Number((meal.nutrients.p * 4) + (meal.nutrients.c * 4) + (meal.nutrients.f * 9)).toFixed(0)}</span>
                        <span className="text-xs text-gray-400 uppercase font-bold tracking-wider">Kcal</span>
                    </>
                 )}
            </div>

            <h4 className="text-lg md:text-xl font-bold text-gray-800 mb-2 leading-tight" title={meal.dish_name}>{meal.dish_name.replace(/\(Veg\)|\(Non-Veg\)/g, '').trim()}</h4>
            <div className="text-sm text-gray-500 font-medium mt-1">
                Portion: <span className="font-bold text-gray-700">
                    {meal.portion_size.replace(/,/g, '+').split('+').map(p => p.trim().split(':')[0]).join(' + ')}
                </span>
            </div>
          </div>

          {/* Adjustment Note */}
          {meal.is_user_adjusted && meal.adjustment_note && (
             <div className="mb-4 px-3 py-2 rounded-xl border border-blue-200 bg-blue-50 text-blue-700 text-xs font-semibold">
               ✏️ {meal.adjustment_note}
             </div>
          )}

          {/* Feast Notes */}
          {meal.feast_notes && meal.feast_notes.length > 0 && (
            <div className="mb-4 space-y-1.5">
              {meal.feast_notes.map((note, idx) => {
                const isSkipped = note === 'SKIPPED';
                const isBanked = note.startsWith('BANKED:');
                const isBanking = !isSkipped && !isBanked && socialEvent?.status !== 'FEAST_DAY';
                const bgColor = isSkipped ? 'bg-gray-100 border-gray-200 text-gray-600'
                  : isBanked ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : isBanking ? 'bg-purple-50 border-purple-200 text-purple-700'
                  : 'bg-amber-50 border-amber-200 text-amber-700';
                return (
                  <div key={idx} className={`px-3 py-2 rounded-xl border text-xs font-semibold ${bgColor}`}>
                    {isSkipped ? 'Meal Skipped — Calories redistributed'
                      : isBanked ? `Banked: ${note.replace('BANKED:', '').trim()}`
                      : note}
                  </div>
                );
              })}
            </div>
          )}

          {/* Collapsible Content */}
          <div className={`transition-all duration-300 overflow-hidden ${isExpanded ? 'opacity-100 max-h-[1000px]' : 'opacity-0 max-h-0 md:opacity-100 md:max-h-[1000px]'}`}>
              <div className="flex flex-col sm:grid sm:grid-cols-5 gap-4 mb-5">
                 <div className="w-full sm:col-span-2 bg-gray-50/80 rounded-2xl flex items-center justify-center p-1">
                     <MacroChart 
                        protein={meal.nutrients.p} 
                        carbs={meal.nutrients.c} 
                        fat={meal.nutrients.f}
                     />
                 </div>
                 <div className="w-full sm:col-span-3 space-y-3 py-1 flex flex-col justify-center">
                    <div className="flex justify-between items-center pb-2 border-b border-dashed border-gray-200">
                       <span className="flex items-center gap-2 text-gray-500 font-semibold text-sm"><div className="w-2 h-2 rounded-full bg-indigo-400"></div> Protein</span>
                       <span className="text-base font-bold text-gray-800">{Number(meal.nutrients.p).toFixed(1)}g</span>
                    </div>
                    <div className="flex justify-between items-center pb-2 border-b border-dashed border-gray-200">
                       <span className="flex items-center gap-2 text-gray-500 font-semibold text-sm"><div className="w-2 h-2 rounded-full bg-emerald-400"></div> Carbs</span>
                       <span className="text-base font-bold text-gray-800">{Number(meal.nutrients.c).toFixed(1)}g</span>
                    </div>
                    <div className="flex justify-between items-center">
                       <span className="flex items-center gap-2 text-gray-500 font-semibold text-sm"><div className="w-2 h-2 rounded-full bg-pink-400"></div> Fat</span>
                       <span className="text-base font-bold text-gray-800">{Number(meal.nutrients.f).toFixed(1)}g</span>
                    </div>
                 </div>
              </div>
              
              <div className="space-y-3 mt-auto border-t border-gray-100 pt-4">
                 {meal.alternatives && meal.alternatives.length > 0 && (
                    <div className="bg-indigo-50/40 p-3.5 rounded-xl border border-indigo-50">
                        <h5 className="text-[11px] font-extrabold text-indigo-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                          Alternatives
                        </h5>
                        <ul className="space-y-1.5">
                           {meal.alternatives.map((alt, idx) => (
                              <li key={idx} className="text-sm text-gray-700 flex items-start gap-2.5 font-medium leading-snug">
                                 <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0"></div>
                                 {alt}
                              </li>
                           ))}
                        </ul>
                    </div>
                 )}

                 {meal.guidelines && meal.guidelines.length > 0 && (
                    <div className="bg-emerald-50/40 p-3.5 rounded-xl border border-emerald-50">
                        <h5 className="text-[11px] font-extrabold text-emerald-600 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                          Guidelines
                        </h5>
                        <ul className="space-y-1.5">
                           {meal.guidelines.map((guide, idx) => (
                              <li key={idx} className="text-sm text-gray-700 flex items-start gap-2.5 font-medium leading-snug">
                                 <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></div>
                                 {guide}
                              </li>
                           ))}
                        </ul>
                    </div>
                 )}
              </div>
          </div>

          {/* Always visible Log Button footer */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex gap-2">
             <button
                 onClick={handleLogToggle}
                 className={`flex-1 py-2 font-bold rounded-xl flex items-center justify-center gap-2 transition-colors ${logId ? "bg-red-50 text-red-600 hover:bg-red-100" : "bg-indigo-50 text-indigo-600 hover:bg-indigo-100"}`}
             >
                 {logId ? (
                    <>
                        <RotateCcw size={18} />
                        Unlog Meal
                    </>
                 ) : (
                    <>
                        <CheckCircle size={18} />
                        Log this Meal
                    </>
                 )}
             </button>
             
             {socialEvent && !logId && meal.portion_size !== 'SKIPPED' && (
               <button
                 onClick={handleSkipMeal}
                 disabled={skipping}
                 className="px-4 py-2 font-bold rounded-xl flex items-center justify-center gap-2 transition-colors bg-gray-50 text-gray-500 hover:bg-orange-50 hover:text-orange-600 border border-gray-200 hover:border-orange-200 disabled:opacity-50"
                 title="Skip this meal and redistribute calories"
               >
                 <SkipForward size={18} />
                 {skipping ? '...' : 'Skip'}
               </button>
             )}
          </div>

        </div>
      </div>
    );
};

export default MealCard;
