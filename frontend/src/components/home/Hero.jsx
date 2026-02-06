import React from 'react';
import { Link } from 'react-router-dom';
import heroImage from '../../images/home_page_workout_2.avif';

const Hero = () => {
  return (
    <section id="home" className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden bg-white">
      {/* Background Shapes & Liquid Effect */}
      <div className="absolute top-0 right-0 -z-10 w-1/2 h-full bg-indigo-50/50 rounded-bl-[100px]"></div>
      
      {/* Liquid Blobs */}
      <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
      <div className="absolute top-0 -right-4 w-72 h-72 bg-indigo-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>

      <div className="container mx-auto px-6">
        <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
          
          {/* Text Content */}
          <div className="flex-1 text-center lg:text-left space-y-8">
            <div className="inline-block px-4 py-1.5 bg-indigo-50 text-indigo-600 font-semibold rounded-full text-sm mb-2 shadow-sm">
              🚀 Transform Your Life Today
            </div>
            
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-gray-900 leading-tight">
              Unlock Your <br className="hidden lg:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
                Peak Performance
              </span>
            </h1>
            
            <p className="text-lg text-gray-600 leading-relaxed max-w-2xl mx-auto lg:mx-0">
              Achieve your dream physique with personalized meal plans and workout routines tailored specifically to your goals. AI-driven nutrition at your fingertips.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
              <Link to="/diet-plan" className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300 w-full sm:w-auto text-center inline-block">
                Get Your Diet Plan
              </Link>
              <button className="px-8 py-4 bg-white text-gray-700 font-bold rounded-full border border-gray-200 hover:border-indigo-200 hover:bg-indigo-50 transition-all duration-300 w-full sm:w-auto">
                Explore Workouts
              </button>
            </div>

            <div className="pt-8 flex items-center justify-center lg:justify-start gap-8">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">10k+</p>
                <p className="text-sm text-gray-500">Happy Users</p>
              </div>
              <div className="w-px h-12 bg-gray-200"></div>
              <div className="text-center">
                 <p className="text-2xl font-bold text-gray-900">500+</p>
                 <p className="text-sm text-gray-500">Recipes</p>
              </div>
              <div className="w-px h-12 bg-gray-200"></div>
               <div className="text-center">
                 <p className="text-2xl font-bold text-gray-900">4.9/5</p>
                 <p className="text-sm text-gray-500">Rating</p>
              </div>
            </div>
          </div>

          {/* Hero Image */}
          <div className="flex-1 relative w-full max-w-lg lg:max-w-xl">
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-[2rem] transform rotate-6 scale-95 opacity-20 blur-sm"></div>
            <img 
              src={heroImage}
              alt="Fitness Athlete" 
              className="relative rounded-[2rem] shadow-2xl object-cover w-full h-[500px] z-10 transform transition-transform hover:scale-[1.02] duration-500"
            />
            
            {/* Float Card 1 */}
            <div className="absolute -bottom-6 -left-6 z-20 bg-white p-4 rounded-xl shadow-xl flex items-center gap-3 animate-bounce-slow">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center text-xl">🥗</div>
              <div>
                <p className="text-sm font-bold text-gray-800">Healthy Diet</p>
                <p className="text-xs text-gray-500">100% Organic</p>
              </div>
            </div>

             {/* Float Card 2 */}
             <div className="absolute top-10 -right-6 z-20 bg-white p-4 rounded-xl shadow-xl flex items-center gap-3 animate-pulse-slow">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center text-xl">🔥</div>
              <div>
                <p className="text-sm font-bold text-gray-800">Burn Fat</p>
                <p className="text-xs text-gray-500">High Intensity</p>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  );
};

export default Hero;
