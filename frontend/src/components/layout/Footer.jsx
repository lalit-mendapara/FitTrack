import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-900 text-gray-300 py-12 border-t border-gray-800">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          
          {/* Brand Column */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-lg">F</span>
              </div>
              <span className="text-2xl font-bold tracking-tight text-white">
                Fit<span className="text-indigo-400">Track</span>
              </span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">
              Empowering your fitness journey with AI-driven insights, personalized meal plans, and holistic health tracking.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-bold mb-4 uppercase text-sm tracking-wider">Quick Links</h3>
            <ul className="space-y-2">
              {['Home', 'About Us', 'Features', 'Pricing', 'Blog'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-gray-400 hover:text-indigo-400 transition-colors text-sm">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

           {/* Support */}
           <div>
            <h3 className="text-white font-bold mb-4 uppercase text-sm tracking-wider">Support</h3>
            <ul className="space-y-2">
              {['Help Center', 'Terms of Service', 'Privacy Policy', 'Contact Support'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-gray-400 hover:text-indigo-400 transition-colors text-sm">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h3 className="text-white font-bold mb-4 uppercase text-sm tracking-wider">Stay Updated</h3>
            <p className="text-xs text-gray-500 mb-4">Subscribe to our newsletter for the latest tips and updates.</p>
            <div className="flex gap-2">
              <input 
                type="email" 
                placeholder="Enter email" 
                className="bg-gray-800 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full text-sm"
              />
              <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors">
                →
              </button>
            </div>
          </div>

        </div>

        <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center text-sm text-gray-500">
          <p>&copy; {new Date().getFullYear()} FitTrack Inc. All rights reserved.</p>
          <div className="flex gap-6 mt-4 md:mt-0">
            <a href="#" className="hover:text-white transition-colors">Twitter</a>
            <a href="#" className="hover:text-white transition-colors">Instagram</a>
            <a href="#" className="hover:text-white transition-colors">LinkedIn</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
