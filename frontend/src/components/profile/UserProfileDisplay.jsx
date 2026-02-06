import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import api from '../../api/axios';
import { useAuth } from '../../context/AuthContext';
import { Info, AlertCircle, Eye, EyeOff } from 'lucide-react';

const UserProfileDisplay = ({ user, isProfileMissing, onLogout, onUpdateProfile }) => {
    const { login } = useAuth(); // We'll use login to update the user in context/localstorage
    const [isEditing, setIsEditing] = useState(false);
    const [isChangingPassword, setIsChangingPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        email: '',
        dob: '',
        gender: '',
        password: '' // Only for password change
    });

    const [passwordData, setPasswordData] = useState({
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
    });

    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    useEffect(() => {
        if (user) {
            setFormData({
                name: user.name || '',
                email: user.email || '',
                dob: user.dob || '',
                gender: user.gender || '',
                password: ''
            });
        }
    }, [user]);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handlePasswordChange = (e) => {
        setPasswordData({ ...passwordData, [e.target.name]: e.target.value });
    };

    const handleUpdateProfile = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Prepare update payload
            const updatePayload = {
                name: formData.name,
                email: formData.email,
                dob: formData.dob,
                gender: formData.gender
            };

            // If changing password
            if (isChangingPassword) {
                if (!passwordData.oldPassword) {
                    toast.error("Please enter your current password.");
                    setLoading(false);
                    return;
                }
                if (passwordData.newPassword !== passwordData.confirmPassword) {
                    toast.error("Passwords do not match!");
                    setLoading(false);
                    return;
                }
                if (passwordData.newPassword.length < 6) {
                    toast.error("Password must be at least 6 characters.");
                    setLoading(false);
                    return;
                }
                updatePayload.password = passwordData.newPassword;
                updatePayload.old_password = passwordData.oldPassword;
            }

            const response = await api.put('/users/me', updatePayload);
            
            // Update context
            // Response is the updated user object
            // If we have a token, we should preserve it. 
            // In a real app we might get a new token or just keep the old one if it's still valid.
            // Here we just update the user data in the context.
            // Note: login function expects (user, token). We can grab token from localstorage.
            const token = localStorage.getItem('diet_planner_token');
            login(response.data, token);

            toast.success("Profile updated successfully!");
            setIsEditing(false);
            setIsChangingPassword(false);
            setPasswordData({ oldPassword: '', newPassword: '', confirmPassword: '' });
            setShowNewPassword(false);
            setShowConfirmPassword(false);

        } catch (err) {
            console.error("Update failed", err);
            const msg = err.response?.data?.detail || "Failed to update profile.";
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const calculateAge = (dobString) => {
        if (!dobString) return 'N/A';
        const dob = new Date(dobString);
        const diff_ms = Date.now() - dob.getTime();
        const age_dt = new Date(diff_ms);
        return Math.abs(age_dt.getUTCFullYear() - 1970);
    };

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
            {/* Informational Alert for Missing Profile - REMOVED */}
            
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">Account Details</h2>
                {!isEditing && (
                    <button 
                        onClick={() => setIsEditing(true)}
                        className="text-indigo-600 font-semibold hover:text-indigo-800 transition-colors"
                    >
                        Edit Details
                    </button>
                )}
            </div>
            
            {isEditing ? (
                <form onSubmit={handleUpdateProfile} className="space-y-6 animate-fadeIn">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                            <input 
                                type="text" 
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                            <input 
                                type="email" 
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Date of Birth</label>
                            <input 
                                type="date" 
                                name="dob"
                                value={formData.dob}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                                required
                            />
                        </div>
                         <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                            <select
                                name="gender"
                                value={formData.gender}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                                required
                            >
                                <option value="" disabled>Select Gender</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                            </select>
                        </div>
                    </div>

                    <div className="pt-4 border-t border-gray-100">
                         <div className="flex items-center justify-between mb-4">
                            <label className="text-sm font-semibold text-gray-700">Password</label>
                            <button 
                                type="button"
                                onClick={() => setIsChangingPassword(!isChangingPassword)}
                                className="text-sm text-indigo-600 hover:text-indigo-800"
                            >
                                {isChangingPassword ? 'Cancel Password Change' : 'Change Password'}
                            </button>
                        </div>
                        
                        {isChangingPassword && (
                            <div className="space-y-4 bg-gray-50 p-6 rounded-xl animate-fadeIn">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Current Password</label>
                                    <input 
                                        type="password" 
                                        name="oldPassword"
                                        value={passwordData.oldPassword}
                                        onChange={handlePasswordChange}
                                        className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                                        placeholder="Enter current password"
                                    />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="relative">
                                        <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                                        <div className="relative">
                                            <input 
                                                type={showNewPassword ? "text" : "password"}
                                                name="newPassword"
                                                value={passwordData.newPassword}
                                                onChange={handlePasswordChange}
                                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all pr-12"
                                                placeholder="Min 6 chars"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowNewPassword(!showNewPassword)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                                            >
                                                {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                            </button>
                                        </div>
                                    </div>
                                    <div className="relative">
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Confirm New Password</label>
                                        <div className="relative">
                                            <input 
                                                type={showConfirmPassword ? "text" : "password"}
                                                name="confirmPassword"
                                                value={passwordData.confirmPassword}
                                                onChange={handlePasswordChange}
                                                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all pr-12"
                                                placeholder="Re-enter password"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                                            >
                                                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="flex gap-4 pt-4">
                        <button 
                            type="button"
                            onClick={() => {
                                setIsEditing(false);
                                setIsChangingPassword(false);
                                // Reset form
                                setFormData({
                                    name: user.name || '',
                                    email: user.email || '',
                                    dob: user.dob || '',
                                    gender: user.gender || '',
                                    password: ''
                                });
                            }}
                            className="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            Cancel
                        </button>
                        <button 
                            type="submit"
                            disabled={loading}
                            className={`px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors shadow-md ${loading ? 'opacity-70 cursor-wait' : ''}`}
                        >
                            {loading ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                     <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Full Name</label>
                        <p className="text-lg font-medium text-gray-900">{user?.name || 'N/A'}</p>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Email Address</label>
                        <p className="text-lg font-medium text-gray-900">{user?.email || 'N/A'}</p>
                    </div>
                    
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Date of Birth</label>
                         {/* Format DOB nicely if desired, using raw string for now */}
                        <p className="text-lg font-medium text-gray-900">{user?.dob || 'N/A'}</p>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Age</label>
                        <p className="text-lg font-medium text-gray-900">{user?.dob ? calculateAge(user.dob) : (user?.age || 'N/A')}</p>
                    </div>

                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Gender</label>
                        <p className="text-lg font-medium text-gray-900 capitalize">{user?.gender || 'N/A'}</p>
                    </div>
                    
                    <div className="space-y-1">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Password</label>
                         <div className="flex items-center gap-2">
                            <span className="text-lg font-medium text-gray-900">••••••••</span>
                            {/* <span className="text-xs text-gray-400">(Hidden)</span> */}
                        </div>
                    </div>
                </div>
            )}

            {/* Mobile Actions Section */}
            {!isEditing && (
                <div className="mt-8 border-t border-gray-100 pt-6 flex flex-col gap-3 md:hidden">
                    <button 
                        onClick={onUpdateProfile}
                        className="w-full flex items-center justify-between p-4 bg-indigo-50 text-indigo-700 rounded-xl font-semibold hover:bg-indigo-100 transition-colors"
                    >
                        <span>Update Fitness Goals & Metrics</span>
                        <Info size={18} />
                    </button>
                    
                    <button 
                        onClick={onLogout}
                        className="w-full flex items-center justify-between p-4 bg-red-50 text-red-600 rounded-xl font-semibold hover:bg-red-100 transition-colors"
                    >
                        <span>Logout</span>
                        <AlertCircle size={18} />
                    </button>
                </div>
            )}
        </div>
    );
};

export default UserProfileDisplay;
