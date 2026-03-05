import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';

const UserDetail = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    fetchUserDetail();
  }, [userId]);

  const fetchUserDetail = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/admin/users/${userId}`, {
        headers: {
          ...adminAuth.getAuthHeader(),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user details');
      }

      const data = await response.json();
      setUser(data);
    } catch (error) {
      console.error('Error fetching user details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          ...adminAuth.getAuthHeader(),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete user');
      }

      alert('User deleted successfully');
      navigate('/admin/users');
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Failed to delete user');
    }
  };

  const handleResetPassword = async () => {
    if (!newPassword || newPassword.length < 8) {
      alert('Password must be at least 8 characters');
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/admin/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...adminAuth.getAuthHeader(),
        },
        body: JSON.stringify({ new_password: newPassword }),
      });

      if (!response.ok) {
        throw new Error('Failed to reset password');
      }

      alert('Password reset successfully');
      setShowResetPasswordModal(false);
      setNewPassword('');
    } catch (error) {
      console.error('Error resetting password:', error);
      alert('Failed to reset password');
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="text-center py-12">Loading user details...</div>
      </AdminLayout>
    );
  }

  if (!user) {
    return (
      <AdminLayout>
        <div className="text-center py-12">User not found</div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate('/admin/users')}
              className="text-purple-600 hover:text-purple-800 mb-2 flex items-center gap-2"
            >
              ← Back to Users
            </button>
            <h1 className="text-3xl font-bold text-gray-900">{user.name}</h1>
            <p className="text-gray-600 mt-2">{user.email}</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowResetPasswordModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Reset Password
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Delete User
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Basic Information</h2>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-gray-500">User ID:</span>
                <p className="font-medium">{user.id}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Name:</span>
                <p className="font-medium">{user.name}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Email:</span>
                <p className="font-medium">{user.email}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Age:</span>
                <p className="font-medium">{user.age || 'Not set'}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Gender:</span>
                <p className="font-medium">{user.gender || 'Not set'}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">Date of Birth:</span>
                <p className="font-medium">{user.dob || 'Not set'}</p>
              </div>
            </div>
          </div>

          {user.profile && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Fitness Profile</h2>
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-gray-500">Weight:</span>
                  <p className="font-medium">{user.profile.weight ? `${user.profile.weight} kg` : 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Height:</span>
                  <p className="font-medium">{user.profile.height ? `${user.profile.height} cm` : 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Weight Goal:</span>
                  <p className="font-medium">{user.profile.weight_goal ? `${user.profile.weight_goal} kg` : 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Fitness Goal:</span>
                  <p className="font-medium">{user.profile.fitness_goal || 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Activity Level:</span>
                  <p className="font-medium">{user.profile.activity_level || 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Diet Type: (Veg/Non-Veg)</span>
                  <p className="font-medium">{user.profile.diet_type || 'Not set'}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Country:</span>
                  <p className="font-medium">{user.profile.country || 'Not set'}</p>
                </div>
              </div>
            </div>
          )}

          {user.profile && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Calculated Macros</h2>
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-gray-500">Daily Calories:</span>
                  <p className="font-medium text-2xl">{user.profile.calories ? `${Math.round(user.profile.calories)} kcal` : 'Not calculated'}</p>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-4">
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <span className="text-sm text-gray-500 block">Protein</span>
                    <p className="font-bold text-lg">{user.profile.protein ? `${Math.round(user.profile.protein)}g` : '-'}</p>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <span className="text-sm text-gray-500 block">Carbs</span>
                    <p className="font-bold text-lg">{user.profile.carbs ? `${Math.round(user.profile.carbs)}g` : '-'}</p>
                  </div>
                  <div className="text-center p-3 bg-yellow-50 rounded-lg">
                    <span className="text-sm text-gray-500 block">Fat</span>
                    <p className="font-bold text-lg">{user.profile.fat ? `${Math.round(user.profile.fat)}g` : '-'}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Activity Summary</h2>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-gray-500">Active Feasts:</span>
                <p className="font-medium">{user.active_feasts_count}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Confirm Delete</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete user <strong>{user.name}</strong>? This action cannot be undone and will delete all related data.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteUser}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Delete User
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Reset Password</h3>
            <p className="text-gray-600 mb-4">
              Enter a new password for <strong>{user.name}</strong>
            </p>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password (min 8 characters)"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 mb-6"
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowResetPasswordModal(false);
                  setNewPassword('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleResetPassword}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Reset Password
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
};

export default UserDetail;
