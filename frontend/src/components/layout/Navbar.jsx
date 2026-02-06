import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import logo from '../../images/Frame 13 2 (2).png';

const Navbar = ({ transparentTextColor = 'text-gray-600' }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 0) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setIsMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLogout = async () => {
    await logout();
    toast.info("You are logged out successfully");
    setTimeout(() => {
      navigate('/', { replace: true });
    }, 2000);
  };

  const navLinkClass = isScrolled 
    ? "text-gray-700 hover:text-indigo-600 font-medium transition-all duration-200 px-4 py-2 rounded-full hover:bg-gray-100/80"
    : `${transparentTextColor} hover:text-indigo-400 font-medium transition-all duration-200 px-4 py-2 rounded-full hover:bg-white/10 backdrop-blur-sm`;

  // Determine text color for mobile menu button
  const mobileButtonClass = isScrolled 
    ? "text-gray-700 hover:text-indigo-600 p-2 rounded-full hover:bg-gray-100/80 transition-all" 
    : `${transparentTextColor} hover:text-indigo-400 p-2 rounded-full hover:bg-white/10 backdrop-blur-sm transition-all`;

  // Dynamic background for unscrolled state based on text color preference
  // strengthened for mobile visibility
  const unscrolledBg = transparentTextColor === 'text-white' 
    ? 'bg-black/60 backdrop-blur-xl shadow-sm border-b border-white/10' 
    : 'bg-white/90 backdrop-blur-xl shadow-sm border-b border-gray-200/50';

  return (
    <nav
      className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-white/95 backdrop-blur-xl shadow-lg border-b border-gray-200/50 py-2'
          : `${unscrolledBg} py-4`
      }`}
    >
      <div className="container mx-auto px-6 flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 cursor-pointer">
          <img 
            src={logo} 
            alt="FitTrack Logo" 
            className="h-10 w-auto object-contain hover:scale-105 transition-transform duration-200 rounded-lg" 
          />
          <span className={`text-2xl font-bold tracking-tight ${isScrolled ? 'text-gray-800' : (transparentTextColor === 'text-white' ? 'text-white' : 'text-gray-800')}`}>
            Fit<span className={isScrolled ? "text-indigo-600" : (transparentTextColor === 'text-white' ? "text-indigo-300" : "text-indigo-600")}>Track</span>
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          <Link to="/" className={navLinkClass}>
            Home
          </Link>
          <Link to="/about" className={navLinkClass}>
            About
          </Link>
          
          <Link 
            to="/profile"
            className={navLinkClass}
          >
            Profile
          </Link>

          <Link 
            to="/diet-plan"
            className={navLinkClass}
          >
            Diet Plan
          </Link>
        </div>

        {/* Auth Buttons or User Profile */}
        <div className="hidden md:flex items-center gap-4">
          {user ? (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-md">
                  {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-gray-800 leading-tight">{user.name}</span>
                  <button 
                    onClick={handleLogout}
                    className="text-xs text-gray-500 hover:text-indigo-600 text-left transition-colors"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <>
              <button 
                onClick={() => navigate('/login')} // Placeholder route for now
                className="px-5 py-2 text-indigo-600 font-semibold hover:bg-indigo-50 rounded-full transition-all duration-200"
              >
                Login
              </button>
              <Link 
                to="/signup"
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-full shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5"
              >
                Sign Up
              </Link>
            </>
          )}
        </div>

        {/* Mobile Menu Button - Replaces Desktop Nav on Mobile */}
        <div className="md:hidden z-[60]">
          <button 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} 
            className={`${mobileButtonClass} focus:outline-none transition-transform duration-300 ${isMobileMenuOpen ? 'rotate-90' : ''}`}
          >
            {isMobileMenuOpen ? (
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile Menu Overlay/Backdrop */}
        <div 
          className={`fixed inset-0 bg-black/70 backdrop-blur-md z-[100] transition-opacity duration-300 ${
            isMobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
          onClick={() => setIsMobileMenuOpen(false)}
        />

        {/* Updated Sidebar Menu - Glassmorphism optimized for readability */}
        <div 
          className={`fixed top-0 right-0 h-screen w-72 bg-white/95 backdrop-blur-2xl z-[110] shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col border-l border-white/20 ${
            isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          {/* Sidebar Header */}
          <div className="flex justify-between items-center p-6 border-b border-gray-100/50">
             <span className="text-xl font-bold text-indigo-600">FitTrack</span>
             <button 
               onClick={() => setIsMobileMenuOpen(false)}
               className="text-gray-500 hover:text-red-500 transition-colors p-2 hover:bg-red-50 rounded-full"
             >
               <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
               </svg>
             </button>
          </div>

          {/* Navigation Links (Matches Desktop Navbar Items) */}
          <div className="flex flex-col px-4 py-6 space-y-1">
            {[
              { label: 'Home', path: '/' },
              { label: 'About', path: '/about' },
              { label: 'Profile', path: '/profile' },
              { label: 'Diet Plan', path: '/diet-plan' }
            ].map((link) => (
              <Link 
                key={link.label}
                to={link.path} 
                className="text-lg font-semibold text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 px-4 py-3 rounded-xl transition-all"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Auth Section (Matches Desktop Login/Signup buttons) */}
          <div className="mt-auto p-6 border-t border-gray-100 bg-gray-50">
            {user ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-white rounded-2xl shadow-sm border border-gray-200">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center text-white font-bold text-xl shadow-md">
                      {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                    </div>
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-base font-bold text-gray-900 truncate">{user.name}</span>
                      <span className="text-xs text-indigo-600 font-semibold uppercase">Active Member</span>
                    </div>
                </div>
                <button 
                  onClick={() => {
                    handleLogout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full py-3.5 bg-red-50 text-red-600 font-bold rounded-xl hover:bg-red-100 transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {/* Mobile Login Button */}
                <button 
                  onClick={() => {
                    navigate('/login');
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full py-3.5 text-indigo-600 font-bold border-2 border-indigo-600 rounded-xl hover:bg-indigo-50 transition-colors"
                >
                  Login
                </button>
                {/* Mobile Signup Button - Styled like Desktop Purple Button */}
                <Link 
                  to="/signup"
                  className="w-full py-3.5 bg-indigo-600 text-white font-bold rounded-xl shadow-md hover:bg-indigo-700 transition-all text-center"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
