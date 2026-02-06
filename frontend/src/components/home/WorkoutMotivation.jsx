import React from 'react';
import motivationImage from '../../images/home_page_workout.avif';

const WorkoutMotivation = () => {
  return (
    <section id="features" className="py-20 bg-white overflow-hidden">
      <div className="container mx-auto px-6">
        <div className="flex flex-col lg:flex-row items-center gap-16 lg:gap-24">
          
          {/* Image Side */}
          <div className="flex-1 w-full order-2 lg:order-1 relative">
            <div className="absolute -top-10 -left-10 w-40 h-40 bg-indigo-100 rounded-full blur-2xl opacity-70"></div>
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-purple-100 rounded-full blur-2xl opacity-70"></div>
            
            <img 
              src={motivationImage}
              alt="Woman Working Out" 
              className="relative rounded-[2rem] shadow-2xl w-full h-[500px] object-cover z-10 hover:sepia-[.2] transition-all duration-500"
            />

            {/* Floating Stat */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white/90 backdrop-blur-sm p-6 rounded-2xl shadow-xl text-center z-20 border border-gray-100">
               <p className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">95%</p>
               <p className="text-sm font-semibold text-gray-700 mt-1">Goal Achievement Rate</p>
            </div>
          </div>

          {/* Text Side */}
          <div className="flex-1 order-1 lg:order-2 space-y-6">
             <div className="inline-block px-4 py-1.5 bg-purple-50 text-purple-600 font-semibold rounded-full text-sm mb-2">
              💪 Strength & Conditioning
            </div>
            
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 leading-tight">
              Train Smart. <br />
              Recover Smarter.
            </h2>
            
            <p className="text-gray-600 text-lg leading-relaxed">
              Fitness isn't just about movement; it's a lifestyle. Our integrated tracking system monitors your workouts, suggests recovery periods, and adapts your nutrition plan instantly based on your calorie expenditure.
            </p>

            <ul className="space-y-4 pt-4">
              {[
                "Personalized Routine Generation",
                "Real-time Calorie Burn Tracking",
                "Progressive Overload Management",
                "Holistic Health Adjustments"
              ].map((item, index) => (
                <li key={index} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center text-green-600 shrink-0">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-gray-700 font-medium">{item}</span>
                </li>
              ))}
            </ul>

            <button className="mt-8 px-8 py-3 bg-gray-900 text-white font-bold rounded-full hover:bg-gray-800 transition-colors shadow-lg">
              Start Your Journey
            </button>
          </div>

        </div>
      </div>
    </section>
  );
};

export default WorkoutMotivation;
