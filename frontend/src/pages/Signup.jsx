import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';

const Signup = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    dob: '',
    gender: ''
  });
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await api.post('/users/signup', formData);

      // Access data directly from response.data (Axios feature)
      const data = response.data;

      // Successful signup
      toast.success('Signup Successful! Welcome to FitTrack.');
      login(data.user, data.access_token); // Login the user with the returned user object and token
      
      // Delay redirect by 2 seconds
      setTimeout(() => {
        navigate('/dashboard'); // Redirect to Dashboard
      }, 2000);
      
    } catch (err) {
      // Axios stores the response data in err.response.data
      const errorMessage = err.response?.data?.detail || 'Signup failed. Please try again.';
      // setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gray-900 overflow-y-auto">
      {/* Background Image */}
      <div 
        className="absolute inset-0 z-0 opacity-40 bg-cover bg-center"
        style={{ 
          backgroundImage: `url('https://images.unsplash.com/photo-1490818387583-1baba5e638af?ixlib=rb-4.0.3&auto=format&fit=crop&w=2064&q=80')` 
        }}
      ></div>
      
      {/* Overlay to ensure text readability if needed, though opacity handles most */}
      <div className="absolute inset-0 bg-black/30 z-0"></div>

      <div className="max-w-md w-full space-y-8 relative z-10 bg-white/10 backdrop-blur-md p-10 rounded-3xl shadow-2xl border border-white/20">
        <div>
          <div className="mx-auto w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg mb-4">
            <span className="text-white font-bold text-xl">F</span>
          </div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-white">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-200">
            Start your journey to a healthier you
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-100 px-4 py-3 rounded-lg text-sm text-center">
              {error}
            </div>
          )}
          
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label htmlFor="name" className="sr-only">Name</label>
              <input
                id="name"
                name="name"
                type="text"
                required
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300/30 placeholder-gray-300 text-white bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm transition-all"
                placeholder="Full Name"
                value={formData.name}
                onChange={handleChange}
              />
            </div>
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300/30 placeholder-gray-300 text-white bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm transition-all"
                placeholder="Email address"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300/30 placeholder-gray-300 text-white bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm transition-all"
                placeholder="Password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
               <div>
                <label htmlFor="dob" className="sr-only">Date of Birth</label>
                <input
                  id="dob"
                  name="dob"
                  type="date"
                  required
                  className="appearance-none relative block w-full px-4 py-3 border border-gray-300/30 text-white bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm transition-all"
                  value={formData.dob}
                  onChange={handleChange}
                />
              </div>
              <div>
                <label htmlFor="gender" className="sr-only">Gender</label>
                <select
                  id="gender"
                  name="gender"
                  required
                  className="appearance-none relative block w-full px-4 py-3 border border-gray-300/30 text-white bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm transition-all [&>option]:text-black"
                  value={formData.gender}
                  onChange={handleChange}
                >
                  <option value="" disabled className="text-gray-500">Gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className={`group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-300 shadow-lg transform hover:-translate-y-0.5 ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              {isLoading ? 'Creating Account...' : 'Sign Up'}
            </button>
          </div>
          
          <div className="text-center">
             <p className="text-sm text-gray-200">
               Already have an account?{' '}
               <Link to="/login" className="font-medium text-indigo-300 hover:text-indigo-200">
                 Log in
               </Link>
             </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Signup;
