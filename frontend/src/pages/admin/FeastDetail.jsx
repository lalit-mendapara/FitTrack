import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { ArrowLeft, Calendar, TrendingUp, User, Utensils, Dumbbell, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

const FeastDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [feast, setFeast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);

  useEffect(() => {
    fetchFeastDetail();
  }, [id]);

  const fetchFeastDetail = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/admin/feasts/${id}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFeast(data);
      } else {
        console.error('Failed to fetch feast details');
      }
    } catch (error) {
      console.error('Error fetching feast details:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      BANKING: 'bg-blue-100 text-blue-800',
      FEAST_DAY: 'bg-purple-100 text-purple-800',
      COMPLETED: 'bg-green-100 text-green-800',
      CANCELLED: 'bg-gray-100 text-gray-800',
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="ml-3 text-gray-600">Loading feast details...</p>
          </div>
        </div>
      </AdminLayout>
    );
  }

  if (!feast) {
    return (
      <AdminLayout>
        <div className="p-6">
          <div className="text-center">
            <p className="text-gray-600">Feast configuration not found</p>
            <button
              onClick={() => navigate('/admin/feasts')}
              className="mt-4 text-blue-600 hover:text-blue-800"
            >
              Back to Feasts
            </button>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-6">
        <div className="mb-6">
          <button
            onClick={() => navigate('/admin/feasts')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Feasts
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Feast Configuration #{feast.id}</h1>
              <p className="text-gray-600 mt-1">{feast.event_name}</p>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge(feast.status)}
              {!feast.is_active && (
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                  Inactive
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <Calendar className="w-8 h-8 text-blue-600" />
              <span className="text-sm text-blue-600 font-medium">Days Until Event</span>
            </div>
            <div className="text-3xl font-bold text-blue-900">{feast.days_until_event}</div>
            <div className="text-sm text-blue-700 mt-1">Event: {formatDate(feast.event_date)}</div>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-8 h-8 text-green-600" />
              <span className="text-sm text-green-600 font-medium">Projected Banked</span>
            </div>
            <div className="text-3xl font-bold text-green-900">{feast.projected_banked_calories}</div>
            <div className="text-sm text-green-700 mt-1">Target: {feast.target_bank_calories} kcal</div>
          </div>

          <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <Utensils className="w-8 h-8 text-orange-600" />
              <span className="text-sm text-orange-600 font-medium">Daily Deduction</span>
            </div>
            <div className="text-3xl font-bold text-orange-900">{feast.daily_deduction}</div>
            <div className="text-sm text-orange-700 mt-1">kcal per day</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <User className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">User Information</h2>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-gray-600">Name:</span>
                <p className="text-gray-900 font-medium">{feast.user_name}</p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Email:</span>
                <p className="text-gray-900 font-medium">{feast.user_email}</p>
              </div>
              <div>
                <span className="text-sm text-gray-600">User ID:</span>
                <p className="text-gray-900 font-medium">#{feast.user_id}</p>
              </div>
              <button
                onClick={() => navigate(`/admin/users/${feast.user_id}`)}
                className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                View User Profile →
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <Calendar className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Timeline</h2>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-gray-600">Start Date:</span>
                <p className="text-gray-900 font-medium">{formatDate(feast.start_date)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Event Date:</span>
                <p className="text-gray-900 font-medium">{formatDate(feast.event_date)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Total Banking Days:</span>
                <p className="text-gray-900 font-medium">{feast.total_banking_days} days</p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Created:</span>
                <p className="text-gray-900 font-medium">{formatDateTime(feast.created_at)}</p>
              </div>
              {feast.updated_at && (
                <div>
                  <span className="text-sm text-gray-600">Last Updated:</span>
                  <p className="text-gray-900 font-medium">{formatDateTime(feast.updated_at)}</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <Utensils className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Base Macros</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Calories:</span>
                <span className="text-gray-900 font-medium">{feast.base_calories.toFixed(0)} kcal</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Protein:</span>
                <span className="text-gray-900 font-medium">{feast.base_protein.toFixed(1)} g</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Carbs:</span>
                <span className="text-gray-900 font-medium">{feast.base_carbs.toFixed(1)} g</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Fat:</span>
                <span className="text-gray-900 font-medium">{feast.base_fat.toFixed(1)} g</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <Dumbbell className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Configuration</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Workout Boost:</span>
                <span className={`font-medium ${feast.workout_boost_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                  {feast.workout_boost_enabled ? '✓ Enabled' : '✗ Disabled'}
                </span>
              </div>
              {feast.user_selected_deduction && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Custom Deduction:</span>
                  <span className="text-gray-900 font-medium">{feast.user_selected_deduction} kcal</span>
                </div>
              )}
              {feast.selected_meals && feast.selected_meals.length > 0 && (
                <div>
                  <span className="text-sm text-gray-600">Selected Meals:</span>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {feast.selected_meals.map((meal) => (
                      <span key={meal} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                        {meal}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {feast.original_diet_snapshot && (
          <div className="bg-white rounded-lg shadow p-6 mt-6">
            <div className="flex items-center mb-4">
              <Utensils className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Original Diet Snapshot</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {(() => {
                // Handle if original_diet_snapshot is a nested object with 'total' and 'meals'
                const snapshotData = feast.original_diet_snapshot;
                
                // Check if it has 'total' and 'meals' structure
                if (snapshotData.total !== undefined && snapshotData.meals) {
                  const meals = typeof snapshotData.meals === 'string' 
                    ? JSON.parse(snapshotData.meals) 
                    : snapshotData.meals;
                  
                  return (
                    <>
                      {/* Total Card */}
                      <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                        <div className="text-xs font-medium text-green-600 uppercase mb-1">Total</div>
                        <div className="text-2xl font-bold text-green-900">{snapshotData.total}</div>
                        <div className="text-xs text-green-700 mt-1">kcal</div>
                      </div>
                      
                      {/* Individual Meal Cards */}
                      {Object.entries(meals).map(([meal, calories]) => (
                        <div key={meal} className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                          <div className="text-xs font-medium text-blue-600 uppercase mb-1">{meal}</div>
                          <div className="text-2xl font-bold text-blue-900">
                            {typeof calories === 'number' ? calories.toFixed(1) : calories}
                          </div>
                          <div className="text-xs text-blue-700 mt-1">kcal</div>
                        </div>
                      ))}
                    </>
                  );
                } else {
                  // Fallback: treat entire object as meal entries
                  return Object.entries(snapshotData).map(([meal, calories]) => {
                    const calorieValue = typeof calories === 'number' 
                      ? calories.toFixed(1) 
                      : typeof calories === 'string' 
                      ? calories 
                      : JSON.stringify(calories);
                    
                    return (
                      <div key={meal} className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                        <div className="text-xs font-medium text-blue-600 uppercase mb-1">{meal}</div>
                        <div className="text-2xl font-bold text-blue-900">{calorieValue}</div>
                        <div className="text-xs text-blue-700 mt-1">kcal</div>
                      </div>
                    );
                  });
                }
              })()}
            </div>
          </div>
        )}

        {feast.feast_workout_data && (
          <div className="bg-white rounded-lg shadow p-6 mt-6">
            <div className="flex items-center mb-4">
              <Dumbbell className="w-5 h-5 text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Feast Workout Plan</h2>
            </div>
            
            {/* Workout Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                <div className="text-sm font-medium text-purple-600 mb-1">Day Name</div>
                <div className="text-lg font-bold text-purple-900">{feast.feast_workout_data.day_name || 'N/A'}</div>
              </div>
              <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                <div className="text-sm font-medium text-green-600 mb-1">Workout Name</div>
                <div className="text-lg font-bold text-green-900">{feast.feast_workout_data.workout_name || 'N/A'}</div>
              </div>
              <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg border border-orange-200">
                <div className="text-sm font-medium text-orange-600 mb-1">Primary Muscle</div>
                <div className="text-lg font-bold text-orange-900">{feast.feast_workout_data.primary_muscle_group || 'N/A'}</div>
              </div>
            </div>

            {/* Exercise Focus */}
            {feast.feast_workout_data.focus && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <div className="text-sm font-medium text-yellow-800 mb-1">Focus</div>
                <div className="text-gray-900">{feast.feast_workout_data.focus}</div>
              </div>
            )}

            {/* Cardio Exercises Carousel */}
            {feast.feast_workout_data.cardio_exercises && feast.feast_workout_data.cardio_exercises.length > 0 && (
              <div className="mb-6">
                <h3 className="text-md font-semibold text-gray-900 mb-3">Cardio Exercises ({feast.feast_workout_data.cardio_exercises.length})</h3>
                <div className="relative">
                  {feast.feast_workout_data.cardio_exercises.length > 1 && (
                    <>
                      <button
                        onClick={() => setCurrentExerciseIndex(prev => 
                          prev === 0 ? feast.feast_workout_data.cardio_exercises.length - 1 : prev - 1
                        )}
                        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100"
                      >
                        <ChevronLeft className="w-5 h-5 text-gray-600" />
                      </button>
                      <button
                        onClick={() => setCurrentExerciseIndex(prev => 
                          prev === feast.feast_workout_data.cardio_exercises.length - 1 ? 0 : prev + 1
                        )}
                        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100"
                      >
                        <ChevronRight className="w-5 h-5 text-gray-600" />
                      </button>
                    </>
                  )}
                  <div className="overflow-hidden px-12">
                    <div 
                      className="flex transition-transform duration-300 ease-in-out"
                      style={{ transform: `translateX(-${currentExerciseIndex * 100}%)` }}
                    >
                      {feast.feast_workout_data.cardio_exercises.map((exercise, idx) => (
                        <div key={idx} className="w-full flex-shrink-0 px-2">
                          <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6 border border-red-200">
                            <div className="flex items-start justify-between mb-4">
                              <div>
                                <h4 className="text-lg font-bold text-red-900 mb-1">{exercise.exercise}</h4>
                                {exercise.image_url && (
                                  <img 
                                    src={exercise.image_url} 
                                    alt={exercise.exercise}
                                    className="w-full h-48 object-cover rounded-lg mt-3 mb-3"
                                    onError={(e) => e.target.style.display = 'none'}
                                  />
                                )}
                              </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="bg-white/50 rounded p-3">
                                <div className="text-xs text-red-600 font-medium">Duration</div>
                                <div className="text-sm font-bold text-red-900">{exercise.duration}</div>
                              </div>
                              <div className="bg-white/50 rounded p-3">
                                <div className="text-xs text-red-600 font-medium">Intensity</div>
                                <div className="text-sm font-bold text-red-900">{exercise.intensity}</div>
                              </div>
                              <div className="bg-white/50 rounded p-3">
                                <div className="text-xs text-red-600 font-medium">Calories Burned</div>
                                <div className="text-sm font-bold text-red-900">{exercise.calories_burned}</div>
                              </div>
                              {exercise.session_duration_min && (
                                <div className="bg-white/50 rounded p-3">
                                  <div className="text-xs text-red-600 font-medium">Session</div>
                                  <div className="text-sm font-bold text-red-900">{exercise.session_duration_min} min</div>
                                </div>
                              )}
                            </div>
                            {exercise.notes && (
                              <div className="mt-3 bg-white/50 rounded p-3">
                                <div className="text-xs text-red-600 font-medium mb-1">Notes</div>
                                <div className="text-sm text-gray-700">{exercise.notes}</div>
                              </div>
                            )}
                            {exercise.instructions && Array.isArray(exercise.instructions) && (
                              <div className="mt-3 bg-white/50 rounded p-3">
                                <div className="text-xs text-red-600 font-medium mb-2">Instructions</div>
                                <ul className="list-disc list-inside space-y-1">
                                  {exercise.instructions.map((instruction, i) => (
                                    <li key={i} className="text-sm text-gray-700">{instruction}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  {feast.feast_workout_data.cardio_exercises.length > 1 && (
                    <div className="flex justify-center mt-4 gap-2">
                      {feast.feast_workout_data.cardio_exercises.map((_, idx) => (
                        <button
                          key={idx}
                          onClick={() => setCurrentExerciseIndex(idx)}
                          className={`w-2 h-2 rounded-full transition-all ${
                            idx === currentExerciseIndex ? 'bg-red-600 w-8' : 'bg-gray-300'
                          }`}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Workout Note */}
            {feast.feast_workout_data.workout_note && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm font-medium text-blue-800 mb-1">Workout Note</div>
                <div className="text-gray-900">{feast.feast_workout_data.workout_note}</div>
              </div>
            )}
          </div>
        )}

      </div>
    </AdminLayout>
  );
};

export default FeastDetail;
