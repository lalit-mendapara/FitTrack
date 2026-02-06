import React from 'react';

const testimonials = [
  {
    id: 1,
    name: 'Sarah Johnson',
    role: 'Weight Loss Journey',
    image: 'https://randomuser.me/api/portraits/women/44.jpg',
    quote: "FitTrack completely changed my relationship with food. The personalized meal plans are delicious and realistic!",
    rating: 5
  },
  {
    id: 2,
    name: 'Michael Chen',
    role: 'Muscle Building',
    image: 'https://randomuser.me/api/portraits/men/32.jpg',
    quote: "I've gained 5kg of muscle in just 3 months. The workout routines combined with the diet plan are a game changer.",
    rating: 5
  },
  {
    id: 3,
    name: 'Emily Davis',
    role: 'Marathon Training',
    image: 'https://randomuser.me/api/portraits/women/68.jpg',
    quote: "As a runner, I needed specific nutrition. FitTrack analyzed my needs perfectly. Energy levels are through the roof!",
    rating: 4
  }
];

const Testimonials = () => {
  return (
    <section id="reviews" className="py-20 bg-gray-50">
      <div className="container mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
            Transformations We're Proud Of
          </h2>
          <p className="text-gray-600 text-lg">
            Join thousands of satisfied users who have achieved their fitness goals with our AI-powered planner.
          </p>
        </div>

        {/* Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {testimonials.map((item) => (
            <div key={item.id} className="bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 cursor-pointer border border-transparent hover:border-indigo-100">
              
              {/* Rating */}
              <div className="flex mb-4">
                {[...Array(5)].map((_, i) => (
                  <svg 
                    key={i} 
                    className={`w-5 h-5 ${i < item.rating ? 'text-yellow-400' : 'text-gray-300'}`} 
                    fill="currentColor" 
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>

              {/* Quote */}
              <p className="text-gray-700 italic mb-6 leading-relaxed">"{item.quote}"</p>

              {/* User Info */}
              <div className="flex items-center gap-4">
                <img 
                  src={item.image} 
                  alt={item.name} 
                  className="w-12 h-12 rounded-full object-cover border-2 border-indigo-100"
                />
                <div>
                  <h4 className="font-bold text-gray-900">{item.name}</h4>
                  <p className="text-xs text-indigo-600 font-medium">{item.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
