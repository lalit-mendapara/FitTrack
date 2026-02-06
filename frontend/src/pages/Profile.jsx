import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { Link } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import UnifiedProfileForm from '../components/profile/UnifiedProfileForm';

const Profile = ({ isEmbedded = false, onProfileComplete, onViewDietPlan, onUpdateStart, onUpdateEnd }) => {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState(null);
  const [workoutData, setWorkoutData] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const response = await api.get('/user-profiles/me');
      setProfileData(response.data);
      
      try {
          const workoutResponse = await api.get('/workout-preferences/me');
          setWorkoutData(workoutResponse.data);
      } catch (workoutErr) {
          console.log("Workout preferences not found, this is expected for new users.", workoutErr);
          setWorkoutData(null);
      }
      
      setShowForm(false);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setProfileData(null);
        setWorkoutData(null);
        setShowForm(true);
      } else {
        console.error("Failed to fetch profile", err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleFormSuccess = (type) => {
    fetchProfile(); 
    if (onProfileComplete) {
       onProfileComplete(type);
    }
  };

  return (
    <div className={`min-h-screen bg-gray-50 ${isEmbedded ? '' : 'pb-20'}`}>
      {!isEmbedded && <Navbar />}
      
      {/* Header Section */}
      <div className={`relative ${isEmbedded ? 'pt-10 pb-10 rounded-3xl mx-6 ' : 'pt-32 pb-20'} bg-gradient-to-r from-indigo-700 to-purple-800 text-white ${isEmbedded ? '' : 'mt-16'}`}>
        <div className={`container mx-auto ${isEmbedded ? 'px-4' : 'px-6'}`}>
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="relative">
              <div className="w-32 h-32 rounded-full bg-white p-1 shadow-2xl">
                <div className="w-full h-full rounded-full bg-indigo-100 flex items-center justify-center text-5xl font-bold text-indigo-600">
                  {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>
              </div>
            </div>
            <div className="text-center md:text-left">
              <h1 className="text-4xl font-bold mb-2">{user?.name}</h1>
              <p className="text-indigo-100 text-lg opacity-90">{user?.email}</p>
              <div className="flex flex-wrap justify-center md:justify-start gap-4 mt-4">
                 <span className="px-4 py-1.5 bg-white/20 rounded-full text-sm backdrop-blur-sm">
                   {user?.gender || 'Gender N/A'}
                 </span>
                 <span className="px-4 py-1.5 bg-white/20 rounded-full text-sm backdrop-blur-sm">
                   Age: {user?.age || 'N/A'}
                 </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 -mt-8 relative z-10">
        {loading ? (
           <div className="bg-white p-12 rounded-2xl shadow-xl flex justify-center">
             <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
           </div>
        ) : (
          <>
            {showForm ? (
                <UnifiedProfileForm 
                    existingProfile={profileData}
                    existingPreferences={workoutData}
                    onSuccess={() => handleFormSuccess('all')} // 'all' indicates both updated
                    onUpdateStart={onUpdateStart}
                    onUpdateEnd={onUpdateEnd}
                />
            ) : (
              <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
                <div className="p-8">
                  <div className="flex justify-between items-center mb-8 border-b pb-4">
                    <h2 className="text-2xl font-bold text-gray-800">Your Physical Profile & Preferences</h2>
                    <div className="flex gap-4">
                      <button 
                        onClick={() => setShowForm(true)}
                        className="px-6 py-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold rounded-lg transition-colors"
                      >
                        Edit Profile & Preferences
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col lg:flex-row gap-8">
                      {/* Left Column: Physical Profile */}
                      <div className="w-full lg:w-3/5">
                          <h3 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-wider flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                            Physical Stats
                          </h3>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                            {/* Stat Card 1 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                              <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Weight</p>
                              <p className="text-xl font-extrabold text-gray-900">{profileData?.weight} <span className="text-sm text-gray-500 font-medium">kg</span></p>
                            </div>

                            {/* Stat Card 2 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                              <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Height</p>
                              <p className="text-xl font-extrabold text-gray-900">{profileData?.height} <span className="text-sm text-gray-500 font-medium">cm</span></p>
                            </div>
                            
                            {/* Stat Card 3 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Goal Weight</p>
                                <p className="text-xl font-extrabold text-indigo-600">{profileData?.weight_goal} <span className="text-sm text-indigo-400 font-medium">kg</span></p>
                            </div>

                                {/* Stat Card 4 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Fitness Goal</p>
                                <p className="text-base font-bold text-gray-800 capitalize truncate" title={profileData?.fitness_goal?.replace('_', ' ')}>{profileData?.fitness_goal?.replace('_', ' ')}</p>
                            </div>
                            
                            {/* Stat Card 5 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Activity Level</p>
                                <p className="text-base font-bold text-gray-800 capitalize truncate" title={profileData?.activity_level?.replace('_', ' ')}>{profileData?.activity_level?.replace('_', ' ')}</p>
                            </div>
                            
                            {/* Stat Card 6 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group">
                                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Diet Type</p>
                                <p className="text-base font-bold text-green-600 capitalize">{profileData?.diet_type?.replace('_', '-')}</p>
                            </div>
                                {/* Stat Card 7 */}
                            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-md transition-all duration-300 group md:col-span-3">
                                <div className="flex justify-between items-center">
                                    <div>
                                        <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1 group-hover:text-indigo-500 transition-colors">Country</p>
                                        <p className="text-base font-bold text-gray-800">{profileData?.country}</p>
                                    </div>
                                    <div className="text-2xl opacity-20 group-hover:opacity-100 transition-opacity">🌍</div>
                                </div>
                            </div>
                          </div>
                      </div>

                      {/* Right Column: Workout Preferences */}
                      <div className="w-full lg:w-2/5">
                           <h3 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-wider flex items-center gap-2">
                             <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                             Workout Preferences
                           </h3>
                           {workoutData ? (
                                <div className="grid grid-cols-2 gap-4">
                                     <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 hover:bg-indigo-50 hover:shadow-md transition-all duration-300">
                                        <p className="text-xs text-indigo-400 uppercase tracking-wide font-semibold mb-1">Experience</p>
                                        <p className="text-lg font-bold text-indigo-900 capitalize">{workoutData.experience_level}</p>
                                     </div>
                                     <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 hover:bg-indigo-50 hover:shadow-md transition-all duration-300">
                                        <p className="text-xs text-indigo-400 uppercase tracking-wide font-semibold mb-1">Frequency</p>
                                        <p className="text-lg font-bold text-indigo-900">{workoutData.days_per_week} Days/wk</p>
                                     </div>
                                      <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 hover:bg-indigo-50 hover:shadow-md transition-all duration-300 col-span-2">
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <p className="text-xs text-indigo-400 uppercase tracking-wide font-semibold mb-1">Session Duration</p>
                                                <p className="text-lg font-bold text-indigo-900">{workoutData.session_duration_min} Minutes</p>
                                            </div>
                                            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                                                ⏱️
                                            </div>
                                        </div>
                                     </div>
                                      {workoutData.health_restrictions && workoutData.health_restrictions !== 'none' && (
                                          <div className="p-4 bg-red-50/50 rounded-xl border border-red-100 hover:bg-red-50 hover:shadow-md transition-all duration-300 col-span-2">
                                            <p className="text-xs text-red-400 uppercase tracking-wide font-semibold mb-1">Health Restrictions</p>
                                            <p className="text-sm text-red-900 leading-relaxed font-medium">{workoutData.health_restrictions}</p>
                                        </div>
                                      )}
                                </div>
                           ) : (
                                <div className="h-40 flex flex-col items-center justify-center p-6 bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl text-center hover:border-indigo-300 transition-colors">
                                    <p className="text-gray-400 text-sm mb-3">No workout preferences set yet.</p>
                                    <button 
                                        onClick={() => setShowForm(true)}
                                        className="px-4 py-2 bg-white text-indigo-600 text-sm font-semibold rounded-lg border border-indigo-100 shadow-sm hover:shadow-md transition-all"
                                    >
                                        Set Preferences
                                    </button>
                                </div>
                           )}
                      </div>
                  </div>
                  
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Profile;
