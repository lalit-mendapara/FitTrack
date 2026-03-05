import React from 'react';
import { Navigate } from 'react-router-dom';
import { adminAuth } from '../../utils/adminAuth';

const AdminProtectedRoute = ({ children }) => {
  if (!adminAuth.isAuthenticated()) {
    return <Navigate to="/admin/login" replace />;
  }

  return children;
};

export default AdminProtectedRoute;
