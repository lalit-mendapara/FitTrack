import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    password: ''
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
      const response = await api.post('/login/json', formData);
      
      const data = response.data;

      // Successful login
      // We need to fetch the user details separately or assume the login returns enough info
      // The backend login/json returns: {"access_token": ..., "token_type": ..., "user_id": ...}
      // It DOES NOT return the full user object (name, etc.) used in the Navbar.
      // We need to fetch the user profile immediately after login.
      
      // Let's first set the basic info we have, but ideally we fetch the /users/me endpoint
      // Updating the login flow to fetch user details.
      
      // 1. Get the profile/user details - assuming the token is needed for this too, 
      // but if /users/me is protected, we need to manually pass the header or set it first.
      // Ideally, the interceptor picks it up if we set it in localStorage, otherwise we pass it explicitly.
      // Since we just got the token, let's use it explicitly for this request or update context first.
      
      // Better approach: Pass token to login() first if we want strict flow, or just use the token in headers.
      // Let's use the token from the response for the /users/me call to be safe before setting global state.
      const token = data.access_token;
      
      const userResponse = await api.get('/users/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      
      toast.success('Login Successful! Welcome back.');
      
      // Delay redirect by 2 seconds
      setTimeout(() => {
         // 2. Login with the user details AND token
         // This triggers the RedirectIfAuthenticated wrapper in App.jsx
         login(userResponse.data, token);
      }, 2000);
      
    } catch (err) {
      console.error(err);
      const errorMessage = err.response?.data?.detail || 'Login failed. Please check your credentials.';
      // setError(errorMessage); // Removed local error state
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gray-900">
      {/* Background Image - Same as Signup for consistency */}
      <div 
        className="absolute inset-0 z-0 opacity-40 bg-cover bg-center"
        style={{ 
          backgroundImage: `url('https://images.unsplash.com/photo-1490818387583-1baba5e638af?ixlib=rb-4.0.3&auto=format&fit=crop&w=2064&q=80')` 
        }}
      ></div>
      
      <div className="absolute inset-0 bg-black/30 z-0"></div>

      <div className="max-w-md w-full space-y-8 relative z-10 bg-white/10 backdrop-blur-md p-10 rounded-3xl shadow-2xl border border-white/20">
        <div>
          <div className="mx-auto w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg mb-4">
            <span className="text-white font-bold text-xl">F</span>
          </div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-white">
            Welcome back
          </h2>
          <p className="mt-2 text-center text-sm text-gray-200">
            Login to access your personalized plan
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
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className={`group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-300 shadow-lg transform hover:-translate-y-0.5 ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </div>
          
          <div className="text-center">
             <p className="text-sm text-gray-200">
               Don't have an account?{' '}
               <Link to="/signup" className="font-medium text-indigo-300 hover:text-indigo-200">
                 Sign up
               </Link>
             </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
