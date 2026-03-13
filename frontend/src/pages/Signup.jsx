import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';

const Signup = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const fileInputRef = useRef(null);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    dob: '',
    gender: ''
  });
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState('');
  const [dateError, setDateError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [profilePicture, setProfilePicture] = useState(null);
  const [profilePicturePreview, setProfilePicturePreview] = useState(null);

  // Allowed special characters for password
  const allowedSpecialChars = '!@#$%&';

  // Function to convert text to camel case (proper case)
  const toCamelCase = (str) => {
    return str
      .toLowerCase()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Email validation function with detailed error messages
  const validateEmail = (email) => {
    if (!email) {
      return '';
    }

    // Check for empty email
    if (email.trim() === '') {
      return '';
    }

    // Check for basic email structure
    if (!email.includes('@')) {
      return 'Email must contain @ symbol';
    }

    // Check for multiple @ symbols
    if (email.split('@').length > 2) {
      return 'Email can only contain one @ symbol';
    }

    // Check if @ is at the beginning or end
    if (email.startsWith('@') || email.endsWith('@')) {
      return '@ symbol cannot be at the beginning or end';
    }

    const [localPart, domain] = email.split('@');

    // Validate local part (before @)
    if (localPart.length === 0) {
      return 'Please enter text before @ symbol';
    }

    if (localPart.length > 64) {
      return 'Text before @ is too long (max 64 characters)';
    }

    // Check for invalid characters in local part
    const localPartRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+$/;
    if (!localPartRegex.test(localPart)) {
      return 'Invalid characters in email address';
    }

    // Check for consecutive dots in local part
    if (localPart.includes('..')) {
      return 'Email cannot contain consecutive dots';
    }

    // Check if local part starts or ends with dot
    if (localPart.startsWith('.') || localPart.endsWith('.')) {
      return 'Email cannot start or end with a dot';
    }

    // Validate domain part (after @)
    if (domain.length === 0) {
      return 'Please enter domain after @ symbol';
    }

    // Check for domain structure
    if (!domain.includes('.')) {
      return 'Domain must contain a dot (e.g., example.com)';
    }

    // Check for domain format
    const domainParts = domain.split('.');
    if (domainParts.length < 2) {
      return 'Invalid domain format';
    }

    // Check each domain part
    for (const part of domainParts) {
      if (part.length === 0) {
        return 'Domain cannot have empty parts';
      }
      
      // Check for invalid characters in domain
      const domainPartRegex = /^[a-zA-Z0-9-]+$/;
      if (!domainPartRegex.test(part)) {
        return 'Domain contains invalid characters';
      }

      // Check if domain part starts or ends with hyphen
      if (part.startsWith('-') || part.endsWith('-')) {
        return 'Domain parts cannot start or end with hyphen';
      }
    }

    // Check top-level domain (last part)
    const tld = domainParts[domainParts.length - 1];
    if (tld.length < 2) {
      return 'Top-level domain must be at least 2 characters';
    }

    if (tld.length > 63) {
      return 'Top-level domain is too long';
    }

    // Check overall email length
    if (email.length > 254) {
      return 'Email address is too long';
    }

    return ''; // No error
  };

  // Password validation function with detailed feedback
  const validatePassword = (password) => {
    if (!password) {
      return { error: '', strength: '', requirements: [] };
    }

    const requirements = [];
    let strength = 0;
    let error = '';

    // Check minimum length
    if (password.length < 8) {
      requirements.push({
        met: false,
        text: 'At least 8 characters'
      });
      error = 'Password must be at least 8 characters long';
    } else {
      requirements.push({
        met: true,
        text: 'At least 8 characters'
      });
      strength += 1;
    }

    // Check for uppercase letter
    if (!/[A-Z]/.test(password)) {
      requirements.push({
        met: false,
        text: 'One uppercase letter (A-Z)'
      });
    } else {
      requirements.push({
        met: true,
        text: 'One uppercase letter (A-Z)'
      });
      strength += 1;
    }

    // Check for lowercase letter
    if (!/[a-z]/.test(password)) {
      requirements.push({
        met: false,
        text: 'One lowercase letter (a-z)'
      });
    } else {
      requirements.push({
        met: true,
        text: 'One lowercase letter (a-z)'
      });
      strength += 1;
    }

    // Check for number
    if (!/[0-9]/.test(password)) {
      requirements.push({
        met: false,
        text: 'One number (0-9)'
      });
    } else {
      requirements.push({
        met: true,
        text: 'One number (0-9)'
      });
      strength += 1;
    }

    // Check for special character
    const specialCharRegex = new RegExp(`[${allowedSpecialChars.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}]`);
    if (!specialCharRegex.test(password)) {
      requirements.push({
        met: false,
        text: `One special character: ${allowedSpecialChars}`
      });
    } else {
      requirements.push({
        met: true,
        text: `One special character: ${allowedSpecialChars}`
      });
      strength += 1;
    }

    // Check for invalid characters
    const validCharRegex = /^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]+$/;
    if (!validCharRegex.test(password)) {
      const invalidChars = password.match(/[^a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/g);
      if (invalidChars) {
        error = `Invalid characters found: ${[...new Set(invalidChars)].join(', ')}. Only use: letters, numbers, and ${allowedSpecialChars}`;
      }
    }

    // Determine strength level
    let strengthText = '';
    if (password.length > 0) {
      if (strength <= 2) strengthText = 'Weak';
      else if (strength === 3) strengthText = 'Fair';
      else if (strength === 4) strengthText = 'Good';
      else if (strength === 5) strengthText = 'Strong';
    }

    // If all requirements are met and no invalid characters, clear error
    if (requirements.every(req => req.met) && !error) {
      error = '';
    }

    return { error, strength: strengthText, requirements };
  };

  // Date validation function for age and future date checking
  const validateDate = (dateString) => {
    if (!dateString) {
      return '';
    }

    const selectedDate = new Date(dateString);
    const today = new Date();
    
    // Clear time part for accurate comparison
    today.setHours(0, 0, 0, 0);
    selectedDate.setHours(0, 0, 0, 0);

    // Check if date is in the future
    if (selectedDate > today) {
      return 'Cannot select a future date';
    }

    // Calculate age
    let age = today.getFullYear() - selectedDate.getFullYear();
    const monthDiff = today.getMonth() - selectedDate.getMonth();
    const dayDiff = today.getDate() - selectedDate.getDate();

    // Adjust age if birthday hasn't occurred this year yet
    if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
      age--;
    }

    // Check if user is under 15 years old
    if (age < 15) {
      return `You are not eligible to signup. You are under 15 years old (${age} years)`;
    }

    return ''; // No error
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    // Apply camel case conversion to name field
    if (name === 'name') {
      setFormData({ ...formData, [name]: toCamelCase(value) });
    } else if (name === 'email') {
      setFormData({ ...formData, [name]: value });
      // Validate email in real-time
      setEmailError(validateEmail(value));
    } else if (name === 'password') {
      setFormData({ ...formData, [name]: value });
      // Validate password in real-time
      const passwordValidation = validatePassword(value);
      setPasswordError(passwordValidation.error);
      setPasswordStrength(passwordValidation.strength);
    } else if (name === 'dob') {
      setFormData({ ...formData, [name]: value });
      // Validate date in real-time
      setDateError(validateDate(value));
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleProfilePictureChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please upload a valid image (JPG, PNG, GIF, or WebP)');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File too large. Max 5MB.');
      return;
    }

    setProfilePicture(file);
    
    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setProfilePicturePreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const removeProfilePicture = () => {
    setProfilePicture(null);
    setProfilePicturePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    // Validate email before submission
    const emailValidationError = validateEmail(formData.email);
    if (emailValidationError) {
      setEmailError(emailValidationError);
      setIsLoading(false);
      return;
    }

    // Validate password before submission
    const passwordValidation = validatePassword(formData.password);
    if (passwordValidation.error) {
      setPasswordError(passwordValidation.error);
      setIsLoading(false);
      return;
    }

    // Validate date before submission
    const dateValidationError = validateDate(formData.dob);
    if (dateValidationError) {
      setDateError(dateValidationError);
      setIsLoading(false);
      return;
    }

    try {
      const response = await api.post('/users/signup', formData);
      const data = response.data;

      // If user uploaded a profile picture, upload it now
      if (profilePicture) {
        try {
          const formData = new FormData();
          formData.append('file', profilePicture);
          const avatarRes = await api.post('/users/upload-avatar', formData, {
            headers: { 
              'Content-Type': 'multipart/form-data',
              'Authorization': `Bearer ${data.access_token}`
            },
          });
          // Update user object with the new profile picture URL
          data.user.profile_picture_url = avatarRes.data.profile_picture_url;
        } catch (avatarErr) {
          console.error('Avatar upload failed during signup', avatarErr);
          // Don't fail signup if avatar upload fails, just log it
          toast.warning('Profile created but photo upload failed. You can upload it later from your profile.');
        }
      }

      toast.success('Signup Successful! Welcome to FitTrack.');
      login(data.user, data.access_token);
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Signup failed. Please try again.';
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
          <div className="mx-auto w-12 h-12 bg-linear-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg mb-4">
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
                className={`appearance-none relative block w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:z-10 sm:text-sm transition-all ${
                  emailError 
                    ? 'border-red-500 bg-red-50/10 text-red-100 focus:border-red-500' 
                    : 'border-gray-300/30 placeholder-gray-300 text-white bg-white/10 focus:border-indigo-500'
                }`}
                placeholder="Email address"
                value={formData.email}
                onChange={handleChange}
              />
              {emailError && (
                <div className="mt-2 text-xs text-red-300 flex items-center">
                  <svg className="w-4 h-4 mr-1 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {emailError}
                </div>
              )}
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  className={`appearance-none relative block w-full px-4 py-3 pr-12 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:z-10 sm:text-sm transition-all ${
                    passwordError 
                      ? 'border-red-500 bg-red-50/10 text-red-100 focus:border-red-500' 
                      : 'border-gray-300/30 placeholder-gray-300 text-white bg-white/10 focus:border-indigo-500'
                  }`}
                  placeholder="Password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-300 focus:outline-none"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              
              {/* Password strength indicator */}
              {passwordStrength && (
                <div className="mt-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-300">Password Strength:</span>
                    <span className={`text-xs font-medium ${
                      passwordStrength === 'Weak' ? 'text-red-400' :
                      passwordStrength === 'Fair' ? 'text-yellow-400' :
                      passwordStrength === 'Good' ? 'text-blue-400' :
                      'text-green-400'
                    }`}>{passwordStrength}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-1.5">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        passwordStrength === 'Weak' ? 'bg-red-400 w-1/4' :
                        passwordStrength === 'Fair' ? 'bg-yellow-400 w-2/4' :
                        passwordStrength === 'Good' ? 'bg-blue-400 w-3/4' :
                        'bg-green-400 w-full'
                      }`}
                    ></div>
                  </div>
                </div>
              )}

              {/* Password requirements */}
              {formData.password && (
                <div className="mt-3 space-y-1">
                  <div className="text-xs text-gray-300 mb-2">Password must contain:</div>
                  {validatePassword(formData.password).requirements.map((req, index) => (
                    <div key={index} className="flex items-center text-xs">
                      <svg 
                        className={`w-3 h-3 mr-2 ${
                          req.met ? 'text-green-400' : 'text-gray-500'
                        }`} 
                        fill="currentColor" 
                        viewBox="0 0 20 20"
                      >
                        {req.met ? (
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        ) : (
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        )}
                      </svg>
                      <span className={req.met ? 'text-green-400' : 'text-gray-400'}>
                        {req.text}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Password error message */}
              {passwordError && (
                <div className="mt-2 text-xs text-red-300 flex items-center">
                  <svg className="w-4 h-4 mr-1 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {passwordError}
                </div>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
               <div>
                <label htmlFor="dob" className="sr-only">Date of Birth</label>
                <input
                  id="dob"
                  name="dob"
                  type="date"
                  required
                  max={new Date().toISOString().split('T')[0]} // Prevent future date selection
                  className={`appearance-none relative block w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:z-10 sm:text-sm transition-all ${
                    dateError 
                      ? 'border-red-500 bg-red-50/10 text-red-100 focus:border-red-500' 
                      : 'border-gray-300/30 text-white bg-white/10 focus:border-indigo-500'
                  } [&>option]:text-black`}
                  value={formData.dob}
                  onChange={handleChange}
                />
                {dateError && (
                  <div className="mt-2 text-xs text-red-300 flex items-center">
                    <svg className="w-4 h-4 mr-1 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {dateError}
                  </div>
                )}
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

          {/* Profile Picture Upload (Optional) */}
          <div className="border-t border-white/10 pt-6">
            <label className="block text-sm font-medium text-gray-200 mb-3">
              Profile Picture <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            
            {profilePicturePreview ? (
              <div className="flex items-center gap-4">
                <img
                  src={profilePicturePreview}
                  alt="Profile preview"
                  className="w-20 h-20 rounded-full object-cover border-2 border-indigo-400"
                />
                <div className="flex-1">
                  <p className="text-sm text-gray-300 mb-2">Photo selected</p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-3 py-1.5 text-xs bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors"
                    >
                      Change
                    </button>
                    <button
                      type="button"
                      onClick={removeProfilePicture}
                      className="px-3 py-1.5 text-xs bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full px-4 py-3 border-2 border-dashed border-gray-300/30 rounded-lg hover:border-indigo-400/50 transition-all bg-white/5 hover:bg-white/10 group"
              >
                <div className="flex flex-col items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-gray-400 group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <div className="text-sm text-gray-300">
                    <span className="text-indigo-300 font-medium">Click to upload</span> or drag and drop
                  </div>
                  <p className="text-xs text-gray-400">PNG, JPG, GIF, WebP up to 5MB</p>
                </div>
              </button>
            )}
            
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              onChange={handleProfilePictureChange}
              className="hidden"
            />
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
