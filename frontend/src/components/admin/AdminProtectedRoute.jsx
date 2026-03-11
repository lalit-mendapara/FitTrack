import  { useEffect } from 'react';
import { adminAuth } from '../../utils/adminAuth';

const AdminProtectedRoute = ({ children }) => {

  useEffect(() => {
    const checkAuth = () => {
      if (!adminAuth.isAuthenticated()) {
        window.location.replace('/admin/login');
      }
    };

    checkAuth();
    // Check token expiration periodically (every minute)
    const interval = setInterval(checkAuth, 60000);

    return () => clearInterval(interval);
  }, []);

  // Return null if initially unauthenticated to prevent flashing protected content
  if (!adminAuth.isAuthenticated()) return null;

  return children;
};

export default AdminProtectedRoute;
