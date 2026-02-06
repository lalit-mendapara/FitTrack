import React from 'react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { Quote, Star, Activity, Heart, Award } from 'lucide-react';
import dietImage from '../images/about_page_diet.avif';
import workoutImage from '../images/about_page_workout.avif';

const About = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar transparentTextColor="text-white" />
      
      {/* Hero Section */}
      <div className="relative pt-32 pb-20 bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-20 bg-[url('https://images.unsplash.com/photo-1543362906-acfc16c67564?ixlib=rb-4.0.3&auto=format&fit=crop&w=1965&q=80')] bg-cover bg-center"></div>
        <div className="container mx-auto px-6 relative z-10 text-center">
           <h1 className="text-5xl md:text-6xl font-extrabold mb-6 tracking-tight leading-tight">
             Wellness is a <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 to-emerald-400">Journey</span>,<br/> Not a Destination.
           </h1>
           <p className="text-xl text-indigo-100 max-w-2xl mx-auto font-light">
             We bring together the wisdom of world-class nutritionists and cutting-edge fitness planning to guide you every step of the way.
           </p>
        </div>
      </div>

      {/* Section 1: Rujuta Diwekar - Nutritional Wisdom */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center gap-12">
            <div className="md:w-1/2 relative">
               <div className="relative z-10 rounded-3xl overflow-hidden shadow-2xl transform rotate-3 hover:rotate-0 transition-all duration-500">
                  <img 
                    src={dietImage}
                    alt="Healthy Indian Food" 
                    className="w-full h-auto object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent flex items-end p-8">
                     <span className="text-white font-bold text-lg">Inspired by Rujuta Diwekar</span>
                  </div>
               </div>
               {/* Decorative Element */}
               <div className="absolute -top-10 -left-10 w-40 h-40 bg-teal-100 rounded-full blur-3xl opacity-50 -z-10"></div>
            </div>
            
            <div className="md:w-1/2">
              <span className="text-emerald-500 font-bold tracking-wider uppercase text-sm mb-2 block">Nutritional Wisdom</span>
              <h2 className="text-4xl font-bold text-gray-900 mb-6 font-serif">"Eat Local, Seasonal, and Traditional"</h2>
              
              <div className="space-y-6 text-lg text-gray-600 leading-relaxed">
                <p>
                   Following the philosophy of India's leading nutritionist, <strong>Rujuta Diwekar</strong>, we believe that diet is not about starvation, but about nourishment. It's about reconnecting with your culinary roots.
                </p>
                
                <div className="bg-emerald-50 p-6 rounded-xl border-l-4 border-emerald-500 mx-4 md:-mx-4">
                  <Quote className="text-emerald-500 mb-2" size={24} />
                  <p className="italic text-gray-800 font-medium">
                     "The secret to good health is not in a pill or a packet, but in your kitchen. Eat what your grandmother ate, and move the way your body wants to."
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
                   <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
                        <Award size={20} />
                      </div>
                      <span className="font-semibold text-gray-800">No Fads</span>
                   </div>
                   <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                        <Heart size={20} />
                      </div>
                      <span className="font-semibold text-gray-800">Listen to Your Body</span>
                   </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Testimonials */}
      <section className="py-20 bg-gray-900 text-white relative overflow-hidden">
        {/* Background Patterns */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-600 rounded-full blur-3xl opacity-20 -translate-y-1/2 translate-x-1/2"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-indigo-600 rounded-full blur-3xl opacity-20 translate-y-1/2 -translate-x-1/2"></div>

        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Success Stories</h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">Real results from real people who transformed their lives with FitTrack.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
             {/* Review 1 */}
             <div className="bg-white/10 backdrop-blur-md p-8 rounded-2xl border border-white/10 hover:border-indigo-500 transition-all duration-300 hover:-translate-y-2">
                <div className="flex text-yellow-400 mb-4 gap-1">
                   {[...Array(5)].map((_, i) => <Star key={i} size={18} fill="currentColor" />)}
                </div>
                <p className="text-gray-300 mb-6 leading-relaxed">"The meal plans are actually doable! I felt my energy levels skyrocket within just two weeks. Finally, a diet that feels like a lifestyle change."</p>
                <div className="flex items-center gap-4">
                   <div className="w-12 h-12 bg-indigo-500 rounded-full flex items-center justify-center text-xl font-bold">S</div>
                   <div>
                      <h4 className="font-bold">Sarah Jenkins</h4>
                      <p className="text-sm text-gray-400">Lost 15kg</p>
                   </div>
                </div>
             </div>

             {/* Review 2 */}
             <div className="bg-white/10 backdrop-blur-md p-8 rounded-2xl border border-white/10 hover:border-indigo-500 transition-all duration-300 hover:-translate-y-2 relative">
                <div className="absolute -top-4 -right-4 bg-indigo-600 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">Top Pick</div>
                <div className="flex text-yellow-400 mb-4 gap-1">
                   {[...Array(5)].map((_, i) => <Star key={i} size={18} fill="currentColor" />)}
                </div>
                <p className="text-gray-300 mb-6 leading-relaxed">"I love how it accounts for Indian regional food. Rujuta's principles really shine through in the veggie options. Highly recommended!"</p>
                <div className="flex items-center gap-4">
                   <div className="w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center text-xl font-bold">R</div>
                   <div>
                      <h4 className="font-bold">Rahul Mehta</h4>
                      <p className="text-sm text-gray-400">Muscle Gain Goal</p>
                   </div>
                </div>
             </div>

             {/* Review 3 */}
             <div className="bg-white/10 backdrop-blur-md p-8 rounded-2xl border border-white/10 hover:border-indigo-500 transition-all duration-300 hover:-translate-y-2">
                <div className="flex text-yellow-400 mb-4 gap-1">
                   {[...Array(5)].map((_, i) => <Star key={i} size={18} fill="currentColor" />)}
                </div>
                <p className="text-gray-300 mb-6 leading-relaxed">"Simple, effective, and beautiful UI. The daily macro breakdown helps me stay on track without obsessing over every calorie."</p>
                <div className="flex items-center gap-4">
                   <div className="w-12 h-12 bg-pink-500 rounded-full flex items-center justify-center text-xl font-bold">E</div>
                   <div>
                      <h4 className="font-bold">Elena Rodriguez</h4>
                      <p className="text-sm text-gray-400">Maintenance</p>
                   </div>
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* Section 3: Workout Wisdom - Nike Training Club / Hevy */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-6">
           <div className="flex flex-col md:flex-row-reverse items-center gap-16">
              <div className="md:w-1/2">
                 <div className="relative rounded-3xl overflow-hidden shadow-2xl group">
                    <img 
                      src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80" 
                      alt="Workout Motivation" 
                      className="w-full h-auto object-cover transform group-hover:scale-105 transition-transform duration-700"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/40 to-transparent flex flex-col justify-end p-8">
                       <span className="text-white bg-indigo-600 px-3 py-1 rounded-full text-xs font-bold w-max mb-2">Nike Training Club Philosophy</span>
                       <h3 className="text-2xl font-bold text-white">"Just Do It."</h3>
                    </div>
                 </div>
              </div>

              <div className="md:w-1/2">
                 <div className="flex items-center gap-3 mb-4">
                    <Activity className="text-indigo-600" size={28} />
                    <span className="text-indigo-600 font-bold tracking-wider uppercase">Movement Philosophy</span>
                 </div>
                 <h2 className="text-4xl font-bold text-gray-900 mb-6">Train for Life, Not Just the Mirror.</h2>
                 <p className="text-lg text-gray-600 mb-8 leading-relaxed">
                    We integrate the core principles of top workout planners like <strong>Nike Training Club</strong> and <strong>Fitbod</strong>. Consistency beats intensity. It's not about the one hour you spend in the gym, but the 23 hours you don't.
                 </p>

                 <div className="space-y-6">
                    <blockquote className="border-l-4 border-indigo-600 pl-6 py-2">
                       <p className="text-xl font-medium text-gray-800 italic mb-2">
                          "There is no finish line. The race is you against you. Every day is a chance to be better than yesterday."
                       </p>
                       <footer className="text-sm text-gray-500 font-bold uppercase tracking-widest">— Inspired by Nike Training Club</footer>
                    </blockquote>

                    <blockquote className="border-l-4 border-purple-600 pl-6 py-2">
                       <p className="text-xl font-medium text-gray-800 italic mb-2">
                          "Strength doesn't come from what you can do. It comes from overcoming the things you once thought you couldn't."
                       </p>
                       <footer className="text-sm text-gray-500 font-bold uppercase tracking-widest">— Fitbod Philosophy</footer>
                    </blockquote>
                 </div>
              </div>
           </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default About;
